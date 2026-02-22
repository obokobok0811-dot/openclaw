"""
GrowthStrategist — 성장 전략 전문가.

시장 기회, 확장 가능성, 고객 세그먼트 성장, 경쟁 환경 변화를
분석하여 성장 전략을 제안한다.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .base_expert import BaseExpert


class GrowthStrategist(BaseExpert):
    name = "GrowthStrategist"
    description = "성장 전략 및 시장 기회 분석 전문가"
    version = "1.0.0"

    GROWTH_KEYWORDS = [
        "expansion", "new market", "partnership", "opportunity",
        "scale", "growth", "acquisition", "launch", "pilot",
        "확장", "신규", "파트너십", "기회", "성장", "인수", "출시",
    ]

    COMPETITOR_KEYWORDS = [
        "competitor", "rival", "alternative", "market share",
        "경쟁사", "대안", "시장점유율",
    ]

    def analyze(self, data: dict) -> dict:
        """
        성장 기회 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails, crm_contacts, market_data, deals

        Returns
        -------
        dict
            growth_score, opportunities[], market_signals[],
            segment_analysis, recommendations[]
        """
        emails = data.get("emails", [])
        contacts = data.get("crm_contacts", [])
        market_data = data.get("market_data", {})
        deals = data.get("deals", [])

        opportunities: List[Dict[str, Any]] = []
        market_signals: List[Dict[str, Any]] = []
        segment_counter: Counter = Counter()

        # 1. 이메일에서 성장 기회 감지
        for email in emails:
            body = email.get("body", "") + " " + email.get("subject", "")
            growth_hits = self._extract_keywords(body, self.GROWTH_KEYWORDS)
            comp_hits = self._extract_keywords(body, self.COMPETITOR_KEYWORDS)

            if growth_hits:
                opportunities.append({
                    "type": "email_growth_signal",
                    "source": email.get("from", "unknown"),
                    "keywords": growth_hits,
                    "impact_score": 6,
                    "urgency": 5,
                    "timestamp": email.get("timestamp"),
                })
            if comp_hits:
                market_signals.append({
                    "type": "competitive_intelligence",
                    "source": email.get("from", "unknown"),
                    "keywords": comp_hits,
                    "impact_score": 5,
                    "urgency": 4,
                })

        # 2. CRM 세그먼트 분석
        for contact in contacts:
            segment = contact.get("segment", "unknown")
            segment_counter[segment] += 1

        # 3. 성장 중인 세그먼트 식별
        growing_segments = []
        for seg, count in segment_counter.most_common(5):
            growing_segments.append({"segment": seg, "contact_count": count})

        # 4. 딜 파이프라인에서 성장 기회
        pipeline_value = sum(d.get("value", 0) for d in deals if d.get("stage") in ("negotiation", "proposal"))
        new_deals = [d for d in deals if d.get("is_new", False)]

        # 5. 성장 점수
        opp_score = min(len(opportunities) * 10, 40)
        pipeline_score = min(pipeline_value / max(market_data.get("target_pipeline", 1), 1) * 30, 30)
        signal_score = min(len(market_signals) * 5, 15)
        segment_score = min(len(growing_segments) * 3, 15)
        growth_score = self._safe_score(opp_score + pipeline_score + signal_score + segment_score)

        # 6. 권고
        recommendations = []
        if new_deals:
            recommendations.append(f"신규 딜 {len(new_deals)}건 확인 — 빠른 후속 조치로 전환율 제고")
        if market_signals:
            recommendations.append(f"경쟁 동향 {len(market_signals)}건 감지 — 차별화 전략 점검 필요")
        if growing_segments:
            top = growing_segments[0]
            recommendations.append(f"'{top['segment']}' 세그먼트 집중 공략 검토 (연락처 {top['contact_count']}건)")

        return {
            "expert": self.name,
            "growth_score": growth_score,
            "opportunities": opportunities,
            "market_signals": market_signals,
            "segment_analysis": growing_segments,
            "pipeline_value": pipeline_value,
            "new_deal_count": len(new_deals),
            "recommendations": recommendations,
        }

    def format_digest(self, results: dict) -> str:
        lines = [
            f"📈 **{self.name}** — 성장 전략 리포트",
            f"   성장 점수: {results['growth_score']:.0f}/100",
            f"   파이프라인 가치: ${results['pipeline_value']:,.0f}",
            f"   기회 감지: {len(results['opportunities'])}건",
            f"   시장 신호: {len(results['market_signals'])}건",
        ]
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
