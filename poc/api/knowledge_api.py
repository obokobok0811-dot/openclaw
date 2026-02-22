#!/usr/bin/env python3
"""
knowledge_api.py - Knowledge Base REST API

Flask API for ingesting URLs and searching the knowledge base.

Endpoints:
    POST /ingest  - URL 수집 → 파싱 → NER → 임베딩 → DB 저장
    GET  /search  - 시맨틱 검색 (query 파라미터)
    GET  /articles - 저장된 article 목록
    GET  /health  - 헬스 체크
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime

# 프로젝트 루트를 path에 추가
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("Flask not installed. Install: pip install flask")
    sys.exit(1)

from poc.knowledge.collector import collect
from poc.knowledge.parser import clean_text
from poc.knowledge.ner import extract_entities, entities_to_json
from poc.knowledge.embeddings import KnowledgeEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Configuration ===
DATA_DIR = os.path.join(PROJECT_ROOT, "poc", "knowledge", "data")
DB_PATH = os.path.join(DATA_DIR, "knowledge.db")
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "poc", "knowledge", "schema.sql")
INDEX_PATH = os.path.join(DATA_DIR, "knowledge.index")

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    """DB 연결을 반환합니다. 필요 시 스키마를 초기화합니다."""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    # 스키마 초기화 (테이블이 없으면)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='articles'"
    )
    if cursor.fetchone() is None:
        if os.path.exists(SCHEMA_PATH):
            with open(SCHEMA_PATH, "r") as f:
                conn.executescript(f.read())
            logger.info("Database schema initialized from schema.sql")
        else:
            logger.error(f"Schema file not found: {SCHEMA_PATH}")

    return conn


# 임베딩 엔진 (lazy init)
_embeddings: KnowledgeEmbeddings | None = None


def get_embeddings() -> KnowledgeEmbeddings:
    """임베딩 엔진 싱글턴을 반환합니다."""
    global _embeddings
    if _embeddings is None:
        _embeddings = KnowledgeEmbeddings(index_path=INDEX_PATH)
    return _embeddings


# === Source weight mapping ===
SOURCE_WEIGHTS = {
    "arxiv.org": 1.5,
    "nature.com": 1.5,
    "science.org": 1.5,
    "github.com": 1.3,
    "stackoverflow.com": 1.2,
    "reuters.com": 1.3,
    "bbc.com": 1.2,
    "nytimes.com": 1.2,
    "wikipedia.org": 1.1,
}


def get_source_weight(url: str) -> float:
    """URL 도메인 기반 source_weight를 반환합니다."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        for key, weight in SOURCE_WEIGHTS.items():
            if key in domain:
                return weight
    except Exception:
        pass
    return 1.0


# === API Endpoints ===


@app.route("/health", methods=["GET"])
def health():
    """헬스 체크."""
    return jsonify({"status": "ok", "service": "knowledge-api"})


@app.route("/ingest", methods=["POST"])
def ingest():
    """
    URL을 수집하여 Knowledge Base에 저장합니다.

    Request body (JSON):
        {"url": "https://example.com/article"}
        Optional: {"url": "...", "source_weight": 1.5}

    Response:
        {"status": "ok", "article_id": 123, "title": "...", "entities": {...}}
    """
    data = request.get_json(force=True, silent=True)
    if not data or "url" not in data:
        return jsonify({"error": "url is required"}), 400

    url = data["url"].strip()
    if not url.startswith(("http://", "https://")):
        return jsonify({"error": "Invalid URL (must start with http:// or https://)"}), 400

    try:
        # 1. 수집
        logger.info(f"Collecting: {url}")
        collected = collect(url)
        title = collected["title"]
        content = collected["content"]
        cleaned = collected["cleaned_text"]

        if not cleaned or len(cleaned) < 50:
            return jsonify({"error": "Insufficient content extracted"}), 422

        # 2. 추가 텍스트 정제
        cleaned = clean_text(cleaned)

        # 3. NER
        entities = extract_entities(cleaned)
        entities_json = entities_to_json(entities)

        # 4. Source weight
        source_weight = data.get("source_weight", get_source_weight(url))

        # 5. DB 저장
        conn = get_db()
        try:
            cursor = conn.execute(
                """
                INSERT INTO articles (url, title, content, cleaned_text, entities, source_weight)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    cleaned_text = excluded.cleaned_text,
                    entities = excluded.entities,
                    source_weight = excluded.source_weight,
                    updated_at = datetime('now')
                """,
                (url, title, content, cleaned, entities_json, source_weight),
            )
            conn.commit()
            article_id = cursor.lastrowid

            # url로 id를 다시 가져옴 (UPSERT의 경우 lastrowid가 부정확할 수 있음)
            row = conn.execute(
                "SELECT id FROM articles WHERE url = ?", (url,)
            ).fetchone()
            if row:
                article_id = row["id"]
        finally:
            conn.close()

        # 6. 임베딩 추가
        emb = get_embeddings()
        # title + cleaned_text 앞부분을 임베딩 (모델 입력 길이 제한)
        embed_text = f"{title}\n{cleaned[:2000]}"
        embedding_id = emb.add(article_id, embed_text)

        if embedding_id is not None:
            # embedding_id를 DB에 업데이트
            conn = get_db()
            try:
                conn.execute(
                    "UPDATE articles SET embedding_id = ? WHERE id = ?",
                    (embedding_id, article_id),
                )
                conn.commit()
            finally:
                conn.close()
            emb.save()

        logger.info(f"Ingested: {title} (id={article_id}, embedding_id={embedding_id})")

        return jsonify({
            "status": "ok",
            "article_id": article_id,
            "title": title,
            "entities": entities,
            "source_weight": source_weight,
            "embedding_id": embedding_id,
        })

    except Exception as e:
        logger.exception(f"Ingest failed for {url}")
        return jsonify({"error": str(e)}), 500


@app.route("/search", methods=["GET"])
def search():
    """
    시맨틱 검색을 수행합니다.

    Query params:
        q: 검색 쿼리 (필수)
        top_k: 결과 수 (기본: 5)

    Response:
        {"results": [{"article_id": 1, "title": "...", "score": 0.95, ...}, ...]}
    """
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "q parameter is required"}), 400

    top_k = request.args.get("top_k", 5, type=int)

    try:
        # articles 메타데이터 로드
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, title, url, created_at, source_weight, entities FROM articles"
            ).fetchall()
        finally:
            conn.close()

        articles_meta = [
            {
                "article_id": r["id"],
                "created_at": r["created_at"],
                "source_weight": r["source_weight"] or 1.0,
            }
            for r in rows
        ]
        articles_lookup = {r["id"]: dict(r) for r in rows}

        # 시맨틱 검색
        emb = get_embeddings()
        results = emb.search(query, top_k=top_k, articles_meta=articles_meta)

        # 결과에 article 정보 추가
        enriched = []
        for r in results:
            article = articles_lookup.get(r["article_id"], {})
            enriched.append({
                "article_id": r["article_id"],
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "semantic_score": round(r["semantic_score"], 4),
                "final_score": round(r["final_score"], 4),
                "entities": json.loads(article.get("entities", "{}")) if article.get("entities") else {},
            })

        return jsonify({"query": query, "results": enriched})

    except Exception as e:
        logger.exception("Search failed")
        return jsonify({"error": str(e)}), 500


@app.route("/articles", methods=["GET"])
def list_articles():
    """저장된 article 목록을 반환합니다."""
    try:
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, url, title, source_weight, created_at, updated_at FROM articles ORDER BY created_at DESC"
            ).fetchall()
        finally:
            conn.close()

        return jsonify({
            "count": len(rows),
            "articles": [dict(r) for r in rows],
        })

    except Exception as e:
        logger.exception("List articles failed")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
