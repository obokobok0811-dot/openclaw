"""
ExpertSynthesizer — 8개 전문가 결과 통합 및 최종 다이제스트 생성.

모든 전문가의 분석 결과를 병합하고, 중복을 제거하며,
우선순위 랭킹을 적용하여 최종 비즈니스 인텔리전스 다이제스트를 생성한다.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Type

from .base_expert import BaseExpert


class ExpertSynthesizer:
    """8개 전문가의 분석 결과를 통합하는 메타 분석기."""

    version = "1.0.0"

    def __init__(
        self,
        expert_classes: Optional[List[Type[BaseExpert]]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Parameters
        ----------
        expert_classes : list[Type[BaseExpert]], optional
            사용할 전문가 클래스 목록. None이면 전체 8개 로드.
        config : dict, optional
            전문가별 설정.
        """
        if expert_classes is None:
            from . import ALL_EXPERTS
            expert_classes = ALL_EXPERTS

        self.config = config or {}
        self.experts: List[BaseExpert] = [
            cls(config=self.config.get(cls.name, {}))
            for cls in expert_classes
        ]

    # ── 분석 실행 ─────────────────────────────────────────────
    def run_all(self, data: dict) -> Dict[str, dict]:
        """
        모든 전문가의 analyze() 를 실행하고 결과를 수집한다.

        Parameters
        ----------
        data : dict
            전문가들에게 전달할 통합 입력 데이터.

        Returns
        -------
        dict
            { expert_name: analyze_result, ... }
        """
        results: Dict[str, dict] = {}
        for expert in self.experts:
            try:
                result = expert.analyze(data)
                results[expert.name] = result
            except Exception as exc:
                results[expert.name] = {
                    "expert": expert.name,
                    "error": str(exc),
                    "recommendations": [],
                }
        return results

    # ── 통합 분석 ─────────────────────────────────────────────
    def synthesize(self, data: dict) -> dict:
        """
        전문가 분석 실행 → 결과 병합 → 중복 제거 → 우선순위 랭킹 → 다이제스트.

        Parameters
        ----------
        data : dict
            통합 입력 데이터.

        Returns
        -------
        dict
            종합 분석 결과.
        """
        raw_results = self.run_all(data)

        # 1. 모든 권고사항 수집 + 출처 태깅
        all_recommendations: List[Dict[str, Any]] = []
        for expert_name, result in raw_results.items():
            for rec in result.get("recommendations", []):
                all_recommendations.append({
                    "text": rec,
                    "source": expert_name,
                })

        # 2. 중복 제거 (유사 텍스트 기반)
        unique_recommendations = self._deduplicate_recommendations(all_recommendations)

        # 3. 모든 발견(findings) 수집 및 우선순위 점수 부여
        all_findings: List[Dict[str, Any]] = []
        # 각 전문가의 알림/위험 항목을 수집
        finding_keys_by_expert = {
            "RevenueGuardian": ["alerts"],
            "GrowthStrategist": ["opportunities", "market_signals"],
            "SkepticalOperator": ["red_flags", "cost_concerns", "bottlenecks"],
            "ProductPulse": ["feature_requests", "pain_points"],
            "ContentAnalyst": ["content_gaps"],
            "SalesEnable": ["hot_leads", "follow_up_suggestions"],
            "CustomerSuccess": ["churn_risk_contacts", "interventions"],
            "ComplianceWatch": ["risk_items", "policy_violations"],
        }

        scorer = BaseExpert.__subclasses__()[0](config={}) if BaseExpert.__subclasses__() else None

        for expert_name, result in raw_results.items():
            keys = finding_keys_by_expert.get(expert_name, [])
            for key in keys:
                items = result.get(key, [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            finding = {**item, "expert_source": expert_name, "finding_type": key}
                            # 우선순위 점수 계산
                            if scorer:
                                finding["priority_score"] = scorer.get_priority_score(item)
                            else:
                                finding["priority_score"] = item.get("impact_score", 5) * 2
                            all_findings.append(finding)

        # 4. 우선순위로 정렬
        all_findings.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        # 5. 종합 점수 계산
        scores = {}
        score_keys = {
            "RevenueGuardian": "revenue_health_score",
            "GrowthStrategist": "growth_score",
            "SkepticalOperator": "operational_risk_score",
            "ProductPulse": "product_health_score",
            "ContentAnalyst": "content_score",
            "SalesEnable": "opportunity_score",
            "CustomerSuccess": None,  # 별도 계산
            "ComplianceWatch": "compliance_score",
        }

        for expert_name, score_key in score_keys.items():
            result = raw_results.get(expert_name, {})
            if score_key:
                scores[expert_name] = result.get(score_key, 0)
            elif expert_name == "CustomerSuccess":
                si = result.get("satisfaction_indicators", {})
                scores[expert_name] = si.get("satisfaction_ratio", 0) * 100

        # 종합 비즈니스 건강 점수 (가중 평균, 리스크 점수는 반전)
        weights = {
            "RevenueGuardian": 0.20,
            "GrowthStrategist": 0.10,
            "SkepticalOperator": 0.15,  # 반전: 100 - risk
            "ProductPulse": 0.10,
            "ContentAnalyst": 0.05,
            "SalesEnable": 0.15,
            "CustomerSuccess": 0.15,
            "ComplianceWatch": 0.10,
        }

        weighted_sum = 0.0
        total_weight = 0.0
        for expert_name, weight in weights.items():
            score = scores.get(expert_name, 50)
            # SkepticalOperator 는 risk 점수이므로 반전
            if expert_name == "SkepticalOperator":
                score = 100 - score
            weighted_sum += score * weight
            total_weight += weight

        overall_health = weighted_sum / max(total_weight, 0.01)

        # 6. 결과 조합
        return {
            "timestamp": time.time(),
            "overall_health_score": round(overall_health, 1),
            "expert_scores": scores,
            "top_findings": all_findings[:20],
            "total_findings": len(all_findings),
            "recommendations": unique_recommendations,
            "total_recommendations": len(unique_recommendations),
            "expert_results": raw_results,
            "experts_run": [e.name for e in self.experts],
        }

    # ── 다이제스트 생성 ───────────────────────────────────────
    def format_digest(self, synthesis: dict) -> str:
        """종합 결과를 한국어 다이제스트로 포맷한다."""
        lines = [
            "═" * 60,
            "📊 비즈니스 인텔리전스 종합 다이제스트",
            "═" * 60,
            f"종합 건강 점수: {synthesis['overall_health_score']:.0f}/100",
            f"분석 전문가: {len(synthesis['experts_run'])}개",
            f"발견 사항: {synthesis['total_findings']}건",
            f"권고 사항: {synthesis['total_recommendations']}건",
            "",
        ]

        # 전문가별 점수 요약
        lines.append("── 전문가별 점수 ──")
        for expert_name, score in synthesis.get("expert_scores", {}).items():
            bar_len = int(score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {expert_name:20s} {bar} {score:.0f}")
        lines.append("")

        # 전문가별 상세 다이제스트
        lines.append("── 전문가별 상세 ──")
        for expert in self.experts:
            result = synthesis.get("expert_results", {}).get(expert.name)
            if result and "error" not in result:
                lines.append(expert.format_digest(result))
                lines.append("")

        # Top 발견 사항
        if synthesis.get("top_findings"):
            lines.append("── 🔝 최우선 발견 사항 (Top 5) ──")
            for i, finding in enumerate(synthesis["top_findings"][:5], 1):
                source = finding.get("expert_source", "?")
                ftype = finding.get("finding_type", "?")
                priority = finding.get("priority_score", 0)
                lines.append(
                    f"  {i}. [{source}] {ftype} — 우선순위 {priority:.1f}"
                )
                # 요약 정보
                if finding.get("type"):
                    lines.append(f"     유형: {finding['type']}")
                if finding.get("contact"):
                    lines.append(f"     대상: {finding['contact']}")
                if finding.get("keywords"):
                    lines.append(f"     키워드: {', '.join(finding['keywords'][:5])}")
            lines.append("")

        # 종합 권고
        if synthesis.get("recommendations"):
            lines.append("── 📌 종합 권고 사항 ──")
            for rec in synthesis["recommendations"]:
                lines.append(f"  • [{rec['source']}] {rec['text']}")

        lines.append("")
        lines.append("═" * 60)
        return "\n".join(lines)

    # ── 편의 메서드 ───────────────────────────────────────────
    def run_and_digest(self, data: dict) -> str:
        """분석 실행 → 통합 → 다이제스트 문자열 반환."""
        synthesis = self.synthesize(data)
        return self.format_digest(synthesis)

    # ── 내부 유틸 ─────────────────────────────────────────────
    @staticmethod
    def _deduplicate_recommendations(
        recs: List[Dict[str, Any]],
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        단순 토큰 오버랩 기반 중복 제거.
        (프로덕션에서는 임베딩 기반으로 교체 가능.)
        """
        unique: List[Dict[str, Any]] = []
        for rec in recs:
            text = rec["text"].lower()
            tokens = set(text.split())
            is_dup = False
            for existing in unique:
                existing_tokens = set(existing["text"].lower().split())
                if not tokens or not existing_tokens:
                    continue
                overlap = len(tokens & existing_tokens) / min(len(tokens), len(existing_tokens))
                if overlap >= similarity_threshold:
                    is_dup = True
                    # 소스 병합
                    if rec["source"] not in existing.get("sources", [existing["source"]]):
                        existing.setdefault("sources", [existing["source"]]).append(rec["source"])
                    break
            if not is_dup:
                unique.append(rec)
        return unique
