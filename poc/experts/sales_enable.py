"""
SalesEnable — 영업 지원 전문가.

영업 기회 감지, 리드 스코어링, 파이프라인 분석을 통해
영업팀의 효율성과 전환율을 극대화한다.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from .base_expert import BaseExpert


class SalesEnable(BaseExpert):
    name = "SalesEnable"
    description = "영업 기회 감지, 리드 스코어링, 파이프라인 분석 전문가"
    version = "1.0.0"

    BUYING_SIGNAL_KEYWORDS = [
        "pricing", "quote", "proposal", "demo", "trial", "purchase",
        "budget", "timeline", "decision", "implement", "contract",
        "가격", "견적", "제안", "데모", "시범", "구매", "예산",
        "일정", "결정", "도입", "계약",
    ]

    OBJECTION_KEYWORDS = [
        "concern", "hesitation", "competitor", "expensive", "delay",
        "not ready", "next quarter", "revisit",
        "우려", "비싸", "지연", "다음분기", "재검토",
    ]

    ENGAGEMENT_WEIGHTS = {
        "email_reply": 10,
        "meeting_scheduled": 25,
        "demo_requested": 30,
        "proposal_requested": 35,
        "pricing_inquiry": 20,
        "website_visit": 5,
        "content_download": 8,
    }

    def analyze(self, data: dict) -> dict:
        """
        영업 관련 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails, crm_contacts, deals, interactions

        Returns
        -------
        dict
            hot_leads[], opportunity_score, follow_up_suggestions[],
            pipeline_health
        """
        emails = data.get("emails", [])
        contacts = data.get("crm_contacts", [])
        deals = data.get("deals", [])
        interactions = data.get("interactions", [])

        hot_leads: List[Dict[str, Any]] = []
        follow_up_suggestions: List[Dict[str, Any]] = []
        lead_scores: Dict[str, float] = {}

        # 1. 이메일에서 구매 신호 감지
        contact_signals: Dict[str, List[str]] = {}
        for email in emails:
            body = email.get("body", "") + " " + email.get("subject", "")
            sender = email.get("from", "unknown")
            buying_hits = self._extract_keywords(body, self.BUYING_SIGNAL_KEYWORDS)
            objection_hits = self._extract_keywords(body, self.OBJECTION_KEYWORDS)

            if buying_hits:
                contact_signals.setdefault(sender, []).extend(buying_hits)

            # 이의 제기 감지 → 후속 조치 제안
            if objection_hits:
                follow_up_suggestions.append({
                    "contact": sender,
                    "type": "address_objection",
                    "objections": objection_hits,
                    "suggested_action": f"'{', '.join(objection_hits)}' 관련 우려 해소 자료 전달",
                    "impact_score": 7,
                    "urgency": 7,
                    "timestamp": email.get("timestamp"),
                })

        # 2. 리드 스코어링
        for contact in contacts:
            contact_id = contact.get("email") or contact.get("id", "unknown")
            score = 0.0

            # 상호작용 기반 점수
            for interaction in interactions:
                if interaction.get("contact_id") == contact.get("id"):
                    action = interaction.get("type", "")
                    score += self.ENGAGEMENT_WEIGHTS.get(action, 3)

            # 이메일 구매 신호 보너스
            signals = contact_signals.get(contact_id, [])
            score += len(signals) * 15

            # 회사 규모/예산 보너스
            company_size = contact.get("company_size", 0)
            if company_size > 500:
                score += 20
            elif company_size > 100:
                score += 10

            # 최근성 보너스
            last_activity = contact.get("last_activity_timestamp")
            if last_activity:
                days_ago = (time.time() - float(last_activity)) / 86400
                if days_ago < 3:
                    score *= 1.5
                elif days_ago < 7:
                    score *= 1.2
                elif days_ago > 30:
                    score *= 0.5

            lead_scores[contact_id] = score

            # 핫 리드 식별 (점수 50 이상)
            if score >= 50:
                hot_leads.append({
                    "contact": contact_id,
                    "name": contact.get("name", ""),
                    "company": contact.get("company", ""),
                    "score": round(score, 1),
                    "buying_signals": signals,
                    "impact_score": 8,
                    "urgency": 8 if score >= 80 else 6,
                })

        # 미응답 리드 후속 조치
        for contact in contacts:
            contact_id = contact.get("email") or contact.get("id", "unknown")
            last_ts = contact.get("last_activity_timestamp")
            if last_ts:
                days_since = (time.time() - float(last_ts)) / 86400
                score = lead_scores.get(contact_id, 0)
                if 7 <= days_since <= 30 and score >= 30:
                    follow_up_suggestions.append({
                        "contact": contact_id,
                        "type": "re_engage",
                        "days_since_last": int(days_since),
                        "lead_score": round(score, 1),
                        "suggested_action": f"{int(days_since)}일간 미활동 — 후속 연락 권장",
                        "impact_score": 5,
                        "urgency": 5,
                    })

        # 3. 파이프라인 건강도
        total_pipeline = sum(d.get("value", 0) for d in deals)
        closing_soon = [d for d in deals if d.get("days_to_close", 999) <= 30]
        stalled = [d for d in deals if d.get("days_stalled", 0) > 14]

        closing_value = sum(d.get("value", 0) for d in closing_soon)
        stalled_value = sum(d.get("value", 0) for d in stalled)

        pipeline_health = {
            "total_value": total_pipeline,
            "deal_count": len(deals),
            "closing_soon_count": len(closing_soon),
            "closing_soon_value": closing_value,
            "stalled_count": len(stalled),
            "stalled_value": stalled_value,
            "velocity_score": self._safe_score(
                (len(closing_soon) / max(len(deals), 1)) * 50
                + (1 - stalled_value / max(total_pipeline, 1)) * 50
            ),
        }

        # 4. 기회 점수 (종합)
        avg_lead_score = (sum(lead_scores.values()) / len(lead_scores)) if lead_scores else 0
        opportunity_score = self._safe_score(
            avg_lead_score * 0.4
            + pipeline_health["velocity_score"] * 0.4
            + len(hot_leads) * 5
        )

        # 5. 권고
        recommendations = []
        hot_leads_sorted = sorted(hot_leads, key=lambda x: x["score"], reverse=True)
        if hot_leads_sorted:
            top = hot_leads_sorted[0]
            recommendations.append(
                f"최우선 리드: {top.get('name', top['contact'])} "
                f"(점수 {top['score']}) — 즉시 접촉 권장"
            )
        if stalled:
            recommendations.append(f"정체 딜 {len(stalled)}건 (${stalled_value:,.0f}) — 원인 파악 및 재활성화")
        if follow_up_suggestions:
            recommendations.append(f"후속 조치 필요 {len(follow_up_suggestions)}건")

        return {
            "expert": self.name,
            "hot_leads": hot_leads_sorted[:10],
            "opportunity_score": opportunity_score,
            "follow_up_suggestions": follow_up_suggestions,
            "pipeline_health": pipeline_health,
            "total_leads_scored": len(lead_scores),
            "recommendations": recommendations,
        }

    def format_digest(self, results: dict) -> str:
        ph = results["pipeline_health"]
        lines = [
            f"🎯 **{self.name}** — 영업 리포트",
            f"   기회 점수: {results['opportunity_score']:.0f}/100",
            f"   핫 리드: {len(results['hot_leads'])}건",
            f"   파이프라인: ${ph['total_value']:,.0f} ({ph['deal_count']}건)",
            f"   곧 마감: {ph['closing_soon_count']}건 (${ph['closing_soon_value']:,.0f})",
            f"   정체 딜: {ph['stalled_count']}건",
        ]
        if results.get("hot_leads"):
            lines.append("   🔥 Top 리드:")
            for lead in results["hot_leads"][:3]:
                lines.append(
                    f"      • {lead.get('name', lead['contact'])} "
                    f"({lead.get('company', '-')}) — 점수 {lead['score']}"
                )
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
