"""
BaseExpert — 모든 비즈니스 분석 전문가의 공통 기반 클래스.

모든 전문가는 이 클래스를 상속하며 다음 인터페이스를 구현한다:
  - analyze(data: dict) → dict
  - get_priority_score(finding: dict) → float
  - format_digest(results: dict) → str
"""

from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseExpert(ABC):
    """비즈니스 분석 전문가 추상 기반 클래스."""

    # 서브클래스에서 오버라이드
    name: str = "BaseExpert"
    description: str = ""
    version: str = "1.0.0"

    # ── 공통 설정 ──────────────────────────────────────────────
    # priority scoring 에서 사용하는 기본 가중치
    DEFAULT_IMPACT_WEIGHT: float = 1.0
    DEFAULT_URGENCY_MULTIPLIER: float = 1.0
    RECENCY_HALF_LIFE_DAYS: float = 7.0  # 7일 반감기

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}

    # ── 추상 메서드 ────────────────────────────────────────────
    @abstractmethod
    def analyze(self, data: dict) -> dict:
        """
        주어진 데이터를 분석하여 결과를 반환한다.

        Parameters
        ----------
        data : dict
            CRM, 이메일, 문서 등에서 추출한 입력 데이터.

        Returns
        -------
        dict
            전문가별 분석 결과. 구체 스키마는 각 전문가 참고.
        """
        ...

    @abstractmethod
    def format_digest(self, results: dict) -> str:
        """
        분석 결과를 한국어 다이제스트로 요약한다.

        Parameters
        ----------
        results : dict
            analyze() 가 반환한 결과.

        Returns
        -------
        str
            사람이 읽을 수 있는 한국어 요약 문자열.
        """
        ...

    # ── 공통 유틸 ──────────────────────────────────────────────
    def get_priority_score(self, finding: dict) -> float:
        """
        발견(finding)의 우선순위 점수를 계산한다.

        공식: impact_score × urgency_multiplier × (1 + recency_boost)

        Parameters
        ----------
        finding : dict
            최소 키: impact_score (0-10), urgency (0-10).
            선택 키: timestamp (epoch seconds).

        Returns
        -------
        float
            우선순위 점수 (높을수록 긴급).
        """
        impact = float(finding.get("impact_score", 5.0))
        urgency = float(finding.get("urgency", 5.0))
        urgency_multiplier = urgency / 5.0  # 5를 기준 1.0 으로 정규화

        # recency_boost: 시간이 지남에 따라 지수적으로 감소
        ts = finding.get("timestamp")
        if ts is not None:
            age_days = max((time.time() - float(ts)) / 86400.0, 0.0)
            recency_boost = math.exp(-0.693 * age_days / self.RECENCY_HALF_LIFE_DAYS)
        else:
            recency_boost = 0.5  # 타임스탬프 없으면 중간값

        return impact * urgency_multiplier * (1.0 + recency_boost)

    # ── 헬퍼 ──────────────────────────────────────────────────
    @staticmethod
    def _extract_keywords(text: str, keywords: List[str]) -> List[str]:
        """텍스트에서 키워드 목록과 일치하는 항목을 반환한다."""
        text_lower = text.lower()
        return [kw for kw in keywords if kw.lower() in text_lower]

    @staticmethod
    def _safe_score(value: float, min_v: float = 0.0, max_v: float = 100.0) -> float:
        """점수를 [min_v, max_v] 범위로 클램프한다."""
        return max(min_v, min(max_v, value))

    def __repr__(self) -> str:
        return f"<{self.name} v{self.version}>"
