#!/usr/bin/env python3
"""
embeddings.py - Sentence-Transformers + FAISS 임베딩/검색 모듈

all-MiniLM-L6-v2 모델을 사용하여 텍스트를 벡터로 변환하고,
FAISS 인덱스로 시맨틱 검색을 수행합니다.

랭킹 공식: final_score = semantic_score * (1 + 0.3 * recency_factor) * source_weight
  - recency_factor = exp(-days_since / tau), tau = 30일
"""

import os
import math
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import numpy as np
except ImportError:
    np = None
    logger.warning("numpy not installed. Install: pip install numpy")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
    logger.warning("sentence-transformers not installed. Install: pip install sentence-transformers")

try:
    import faiss
except ImportError:
    faiss = None
    logger.warning("faiss not installed. Install: pip install faiss-cpu")

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 출력 차원

# 랭킹 파라미터
TAU_DAYS = 30  # recency decay half-life


class KnowledgeEmbeddings:
    """Knowledge Base 임베딩 및 검색 엔진."""

    def __init__(
        self,
        index_path: str = "poc/knowledge/data/knowledge.index",
        ids_path: Optional[str] = None,
    ):
        """
        Args:
            index_path: FAISS 인덱스 파일 경로
            ids_path: article ID 매핑 파일 경로 (기본: index_path + '.ids')
        """
        self.index_path = index_path
        self.ids_path = ids_path or (index_path + ".ids")
        self.model = None
        self.index = None
        self.id_map: list[int] = []  # FAISS row -> article_id

        self._load_model()
        self._load_index()

    def _load_model(self):
        """sentence-transformers 모델 로드."""
        if SentenceTransformer is None:
            logger.error("sentence-transformers required but not installed")
            return
        try:
            self.model = SentenceTransformer(MODEL_NAME)
            logger.info(f"Loaded model: {MODEL_NAME}")
        except Exception as e:
            logger.error(f"Failed to load model {MODEL_NAME}: {e}")

    def _load_index(self):
        """기존 FAISS 인덱스 로드 (없으면 새로 생성)."""
        if faiss is None or np is None:
            return

        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                logger.info(f"Loaded FAISS index: {self.index_path} ({self.index.ntotal} vectors)")
            except Exception as e:
                logger.warning(f"Failed to load index, creating new: {e}")
                self.index = faiss.IndexFlatIP(EMBEDDING_DIM)  # Inner Product (cosine sim with normalized vectors)
        else:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            self.index = faiss.IndexFlatIP(EMBEDDING_DIM)
            logger.info("Created new FAISS index (IndexFlatIP)")

        # ID 매핑 로드
        if os.path.exists(self.ids_path):
            try:
                with open(self.ids_path, "r") as f:
                    self.id_map = [int(line.strip()) for line in f if line.strip()]
            except Exception as e:
                logger.warning(f"Failed to load ID map: {e}")
                self.id_map = []

    def encode(self, text: str) -> Optional[list[float]]:
        """
        텍스트를 임베딩 벡터로 변환합니다.

        Args:
            text: 입력 텍스트

        Returns:
            임베딩 벡터 (list[float]) 또는 None
        """
        if self.model is None or np is None:
            return None

        try:
            embedding = self.model.encode([text], normalize_embeddings=True)
            return embedding[0].tolist()
        except Exception as e:
            logger.error(f"Encoding failed: {e}")
            return None

    def add(self, article_id: int, text: str) -> Optional[int]:
        """
        텍스트를 임베딩하여 인덱스에 추가합니다.

        Args:
            article_id: DB article ID
            text: 임베딩할 텍스트

        Returns:
            FAISS 인덱스 내 row index, 또는 None
        """
        if self.model is None or self.index is None or np is None:
            return None

        try:
            embedding = self.model.encode([text], normalize_embeddings=True)
            vec = np.array(embedding).astype("float32")
            self.index.add(vec)
            embedding_id = self.index.ntotal - 1
            self.id_map.append(article_id)
            return embedding_id
        except Exception as e:
            logger.error(f"Failed to add embedding: {e}")
            return None

    def search(
        self,
        query: str,
        top_k: int = 10,
        articles_meta: Optional[list[dict]] = None,
    ) -> list[dict]:
        """
        쿼리로 시맨틱 검색을 수행합니다.

        Args:
            query: 검색 쿼리
            top_k: 반환할 결과 수
            articles_meta: 각 article의 메타데이터 리스트
                [{"article_id": int, "created_at": str, "source_weight": float}, ...]
                랭킹 재조정에 사용

        Returns:
            [{
                "article_id": int,
                "semantic_score": float,
                "final_score": float,
                "embedding_id": int
            }, ...]
        """
        if self.model is None or self.index is None or np is None:
            return []
        if self.index.ntotal == 0:
            return []

        try:
            query_vec = self.model.encode([query], normalize_embeddings=True)
            query_vec = np.array(query_vec).astype("float32")

            # top_k는 인덱스 크기를 초과할 수 없음
            k = min(top_k, self.index.ntotal)
            scores, indices = self.index.search(query_vec, k)

            results = []
            # articles_meta를 article_id 기준 dict로 변환
            meta_map = {}
            if articles_meta:
                for m in articles_meta:
                    meta_map[m.get("article_id")] = m

            for score, idx in zip(scores[0], indices[0]):
                if idx < 0:
                    continue

                article_id = self.id_map[idx] if idx < len(self.id_map) else idx
                semantic_score = float(score)

                # 랭킹 재조정
                final_score = self._compute_final_score(
                    semantic_score, article_id, meta_map
                )

                results.append({
                    "article_id": article_id,
                    "semantic_score": semantic_score,
                    "final_score": final_score,
                    "embedding_id": int(idx),
                })

            # final_score 내림차순 정렬
            results.sort(key=lambda x: x["final_score"], reverse=True)
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _compute_final_score(
        self, semantic_score: float, article_id: int, meta_map: dict
    ) -> float:
        """
        랭킹 공식 적용:
        final_score = semantic_score * (1 + 0.3 * recency_factor) * source_weight
        recency_factor = exp(-days_since / tau), tau = 30
        """
        meta = meta_map.get(article_id, {})
        source_weight = meta.get("source_weight", 1.0)
        created_at_str = meta.get("created_at")

        recency_factor = 0.0
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                days_since = (now - created_at).total_seconds() / 86400
                recency_factor = math.exp(-days_since / TAU_DAYS)
            except (ValueError, TypeError):
                pass

        final_score = semantic_score * (1 + 0.3 * recency_factor) * source_weight
        return final_score

    def save(self):
        """인덱스와 ID 매핑을 디스크에 저장합니다."""
        if self.index is None or faiss is None:
            return

        try:
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            faiss.write_index(self.index, self.index_path)
            with open(self.ids_path, "w") as f:
                for aid in self.id_map:
                    f.write(f"{aid}\n")
            logger.info(f"Saved index ({self.index.ntotal} vectors) to {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    @property
    def total_vectors(self) -> int:
        """인덱스에 저장된 벡터 수."""
        return self.index.ntotal if self.index else 0


if __name__ == "__main__":
    # 간단한 테스트
    emb = KnowledgeEmbeddings()
    print(f"Model loaded: {emb.model is not None}")
    print(f"Index vectors: {emb.total_vectors}")

    if emb.model:
        vec = emb.encode("테스트 문장입니다")
        if vec:
            print(f"Embedding dim: {len(vec)}")
            print(f"First 5 values: {vec[:5]}")
