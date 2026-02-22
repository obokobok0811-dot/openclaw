"""
CustomerSuccess — 고객 성공 전문가.

고객 만족도 추적, 이탈 위험 감지, 관계 건강도 모니터링을 통해
고객 유지율을 극대화한다.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from .base_expert import BaseExpert


class CustomerSuccess(BaseExpert):
    name = "CustomerSuccess"
    description = "고객 만족도 추적, 이탈 위험 감지, 관계 건강도 전문가"
    version = "1.0.0"

    SATISFACTION_POSITIVE = [
        "thank", "appreciate", "happy", "satisfied", "great job",
        "well done", "impressive", "pleased", "recommend",
        "감사", "만족", "훌륭", "추천", "잘했",
    ]

    SATISFACTION_NEGATIVE = [
        "disappointed", "unhappy", "dissatisfied", "complaint",
        "escalate", "unacceptable", "switch", "alternative",
        "실망", "불만", "불쾌", "해지", "전환", "대안",
    ]

    CHURN_RISK_KEYWORDS = [
        "cancel", "terminate", "end contract", "not renewing",
        "looking at alternatives", "switch provider", "too expensive",
        "해지", "종료", "갱신안함", "대안검토", "비용문제",
    ]

    ENGAGEMENT_THRESHOLDS = {
        "high": 10,      # 30일 내 10회 이상 상호작용
        "medium": 5,     # 5~9회
        "low": 2,        # 2~4회
        "dormant": 0,    # 0~1회
    }

    def analyze(self, data: dict) -> dict:
        """
        고객 성공 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails, crm_contacts, support_tickets, usage_data

        Returns
        -------
        dict
            churn_risk_contacts[], satisfaction_indicators,
            engagement_scores, interventions[]
        """
        emails = data.get("emails", [])
        contacts = data.get("crm_contacts", [])
        tickets = data.get("support_tickets", [])
        usage = data.get("usage_data", [])

        churn_risk_contacts: List[Dict[str, Any]] = []
        interventions: List[Dict[str, Any]] = []
        engagement_scores: Dict[str, Dict[str, Any]] = {}

        # 연락처별 이메일 빈도 및 감성 집계
        contact_email_stats: Dict[str, Dict[str, Any]] = {}
        for email in emails:
            sender = email.get("from", "unknown")
            stats = contact_email_stats.setdefault(sender, {
                "count": 0, "positive": 0, "negative": 0,
                "churn_signals": 0, "last_ts": 0,
            })
            stats["count"] += 1

            body = email.get("body", "") + " " + email.get("subject", "")
            pos = len(self._extract_keywords(body, self.SATISFACTION_POSITIVE))
            neg = len(self._extract_keywords(body, self.SATISFACTION_NEGATIVE))
            churn = len(self._extract_keywords(body, self.CHURN_RISK_KEYWORDS))

            stats["positive"] += pos
            stats["negative"] += neg
            stats["churn_signals"] += churn

            ts = email.get("timestamp", 0)
            if ts and float(ts) > stats["last_ts"]:
                stats["last_ts"] = float(ts)

        # 연락처별 지원 티켓 수 집계
        contact_tickets: Dict[str, int] = {}
        open_tickets: Dict[str, int] = {}
        for ticket in tickets:
            cid = ticket.get("contact_id", "unknown")
            contact_tickets[cid] = contact_tickets.get(cid, 0) + 1
            if ticket.get("status") == "open":
                open_tickets[cid] = open_tickets.get(cid, 0) + 1

        # 사용량 데이터 (연락처 / 회사 기준)
        usage_map: Dict[str, Dict[str, Any]] = {}
        for u in usage:
            uid = u.get("contact_id") or u.get("company_id", "unknown")
            usage_map[uid] = u

        # 연락처 분석
        now = time.time()
        overall_positive = 0
        overall_negative = 0

        for contact in contacts:
            cid = contact.get("email") or contact.get("id", "unknown")
            email_stats = contact_email_stats.get(cid, {
                "count": 0, "positive": 0, "negative": 0,
                "churn_signals": 0, "last_ts": 0,
            })

            # 참여도 점수
            interaction_count = email_stats["count"] + contact_tickets.get(cid, 0)
            if interaction_count >= self.ENGAGEMENT_THRESHOLDS["high"]:
                eng_level = "high"
            elif interaction_count >= self.ENGAGEMENT_THRESHOLDS["medium"]:
                eng_level = "medium"
            elif interaction_count >= self.ENGAGEMENT_THRESHOLDS["low"]:
                eng_level = "low"
            else:
                eng_level = "dormant"

            # 이탈 위험 계산
            churn_score = 0.0
            reasons = []

            # 직접적 이탈 신호
            if email_stats["churn_signals"] > 0:
                churn_score += email_stats["churn_signals"] * 25
                reasons.append(f"이탈 키워드 {email_stats['churn_signals']}건")

            # 부정 감성 높음
            if email_stats["negative"] > email_stats["positive"] and email_stats["negative"] >= 2:
                churn_score += 20
                reasons.append("부정 감성 우세")

            # 장기 미활동
            if email_stats["last_ts"] > 0:
                days_since = (now - email_stats["last_ts"]) / 86400
                if days_since > 60:
                    churn_score += 30
                    reasons.append(f"{int(days_since)}일 미활동")
                elif days_since > 30:
                    churn_score += 15
                    reasons.append(f"{int(days_since)}일 미활동")

            # 미해결 티켓 많음
            open_count = open_tickets.get(cid, 0)
            if open_count >= 3:
                churn_score += 15
                reasons.append(f"미해결 티켓 {open_count}건")

            # 사용량 감소
            u = usage_map.get(cid, {})
            usage_trend = u.get("trend_pct", 0)
            if usage_trend < -20:
                churn_score += 20
                reasons.append(f"사용량 {usage_trend:.0f}% 감소")

            churn_score = min(churn_score, 100)

            engagement_scores[cid] = {
                "level": eng_level,
                "interaction_count": interaction_count,
                "sentiment_ratio": (
                    email_stats["positive"] / max(email_stats["positive"] + email_stats["negative"], 1)
                ),
            }

            overall_positive += email_stats["positive"]
            overall_negative += email_stats["negative"]

            # 이탈 위험 고객 목록
            if churn_score >= 40:
                churn_risk_contacts.append({
                    "contact": cid,
                    "name": contact.get("name", ""),
                    "company": contact.get("company", ""),
                    "churn_score": round(churn_score, 1),
                    "reasons": reasons,
                    "engagement_level": eng_level,
                    "impact_score": 9 if churn_score >= 70 else 7,
                    "urgency": 9 if churn_score >= 70 else 6,
                    "contract_value": contact.get("contract_value", 0),
                })

            # 개입 필요 고객
            if churn_score >= 60:
                interventions.append({
                    "contact": cid,
                    "name": contact.get("name", ""),
                    "type": "urgent_outreach",
                    "churn_score": round(churn_score, 1),
                    "suggested_action": f"긴급 연락: {', '.join(reasons)}",
                    "priority": "critical" if churn_score >= 80 else "high",
                })
            elif eng_level == "dormant" and churn_score >= 30:
                interventions.append({
                    "contact": cid,
                    "name": contact.get("name", ""),
                    "type": "re_engagement",
                    "churn_score": round(churn_score, 1),
                    "suggested_action": "재참여 캠페인: 가치 제안 리마인더 발송",
                    "priority": "medium",
                })

        # 만족도 지표 종합
        total_signals = overall_positive + overall_negative
        satisfaction_indicators = {
            "overall_positive": overall_positive,
            "overall_negative": overall_negative,
            "satisfaction_ratio": (
                overall_positive / max(total_signals, 1)
            ),
            "nps_estimate": round(
                (overall_positive - overall_negative) / max(total_signals, 1) * 100, 1
            ),
        }

        # 정렬
        churn_risk_contacts.sort(key=lambda x: x["churn_score"], reverse=True)

        # 권고
        recommendations = []
        at_risk_value = sum(c.get("contract_value", 0) for c in churn_risk_contacts)
        if churn_risk_contacts:
            recommendations.append(
                f"이탈 위험 고객 {len(churn_risk_contacts)}건 "
                f"(계약가치 ${at_risk_value:,.0f}) — 즉시 관리 필요"
            )
        critical = [i for i in interventions if i["priority"] == "critical"]
        if critical:
            recommendations.append(f"긴급 개입 필요 {len(critical)}건")
        dormant_count = sum(1 for v in engagement_scores.values() if v["level"] == "dormant")
        if dormant_count:
            recommendations.append(f"휴면 고객 {dormant_count}건 — 재활성화 캠페인 검토")
        if satisfaction_indicators["satisfaction_ratio"] < 0.6:
            recommendations.append("전반적 만족도 저하 — 고객 경험 개선 프로그램 필요")

        return {
            "expert": self.name,
            "churn_risk_contacts": churn_risk_contacts[:20],
            "satisfaction_indicators": satisfaction_indicators,
            "engagement_scores": engagement_scores,
            "interventions": interventions,
            "recommendations": recommendations,
        }

    def format_digest(self, results: dict) -> str:
        si = results["satisfaction_indicators"]
        lines = [
            f"🤝 **{self.name}** — 고객 성공 리포트",
            f"   만족도 비율: {si['satisfaction_ratio']:.0%}",
            f"   NPS 추정: {si['nps_estimate']:+.0f}",
            f"   이탈 위험 고객: {len(results['churn_risk_contacts'])}건",
            f"   개입 필요: {len(results['interventions'])}건",
        ]
        if results.get("churn_risk_contacts"):
            lines.append("   ⚠️ 이탈 위험 Top:")
            for c in results["churn_risk_contacts"][:3]:
                lines.append(
                    f"      • {c.get('name', c['contact'])} "
                    f"({c.get('company', '-')}) — 위험도 {c['churn_score']}"
                )
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
