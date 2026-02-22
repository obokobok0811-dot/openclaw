"""
RevenueGuardian — 매출 보호 전문가.

매출 흐름의 이상 징후, 결제 지연, 계약 만료 등을 감지하여
매출 손실을 사전에 방지한다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_expert import BaseExpert


class RevenueGuardian(BaseExpert):
    name = "RevenueGuardian"
    description = "매출 보호 및 수익 이상 감지 전문가"
    version = "1.0.0"

    # 매출 관련 키워드
    REVENUE_KEYWORDS = [
        "invoice", "payment", "overdue", "cancel", "refund",
        "churn", "downgrade", "renewal", "contract", "billing",
        "미수금", "결제", "환불", "해지", "연체", "갱신", "계약",
    ]

    RISK_THRESHOLDS = {
        "overdue_days_warning": 30,
        "overdue_days_critical": 60,
        "revenue_drop_pct": 10.0,
    }

    def analyze(self, data: dict) -> dict:
        """
        매출 관련 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails (list[dict]), crm_deals (list[dict]),
                  invoices (list[dict]), revenue_metrics (dict)

        Returns
        -------
        dict
            revenue_health_score, at_risk_revenue, alerts[], recommendations[]
        """
        emails = data.get("emails", [])
        invoices = data.get("invoices", [])
        crm_deals = data.get("crm_deals", [])
        metrics = data.get("revenue_metrics", {})

        alerts: List[Dict[str, Any]] = []
        at_risk_revenue = 0.0

        # 1. 이메일에서 매출 위험 신호 감지
        for email in emails:
            body = email.get("body", "") + " " + email.get("subject", "")
            matched = self._extract_keywords(body, self.REVENUE_KEYWORDS)
            if matched:
                risk_kws = {"cancel", "refund", "churn", "downgrade", "해지", "환불"}
                is_risk = bool(set(k.lower() for k in matched) & risk_kws)
                if is_risk:
                    alerts.append({
                        "type": "email_risk_signal",
                        "source": email.get("from", "unknown"),
                        "keywords": matched,
                        "impact_score": 7,
                        "urgency": 8,
                        "timestamp": email.get("timestamp"),
                    })

        # 2. 연체 인보이스 확인
        for inv in invoices:
            overdue_days = inv.get("overdue_days", 0)
            if overdue_days >= self.RISK_THRESHOLDS["overdue_days_critical"]:
                amount = inv.get("amount", 0)
                at_risk_revenue += amount
                alerts.append({
                    "type": "critical_overdue",
                    "invoice_id": inv.get("id"),
                    "amount": amount,
                    "overdue_days": overdue_days,
                    "impact_score": 9,
                    "urgency": 9,
                })
            elif overdue_days >= self.RISK_THRESHOLDS["overdue_days_warning"]:
                amount = inv.get("amount", 0)
                at_risk_revenue += amount * 0.5
                alerts.append({
                    "type": "overdue_warning",
                    "invoice_id": inv.get("id"),
                    "amount": amount,
                    "overdue_days": overdue_days,
                    "impact_score": 6,
                    "urgency": 6,
                })

        # 3. 딜 파이프라인 위험
        for deal in crm_deals:
            if deal.get("status") == "at_risk":
                at_risk_revenue += deal.get("value", 0)
                alerts.append({
                    "type": "deal_at_risk",
                    "deal_name": deal.get("name"),
                    "value": deal.get("value", 0),
                    "impact_score": 8,
                    "urgency": 7,
                })

        # 4. 매출 건강 점수 계산
        base_score = 100.0
        penalty = len(alerts) * 5 + (at_risk_revenue / max(metrics.get("mrr", 1), 1)) * 30
        revenue_health_score = self._safe_score(base_score - penalty)

        # 5. 권고사항 생성
        recommendations = []
        if at_risk_revenue > 0:
            recommendations.append(f"위험 매출 ${at_risk_revenue:,.0f} 에 대한 즉시 후속 조치 필요")
        if any(a["type"] == "critical_overdue" for a in alerts):
            recommendations.append("60일 이상 연체 인보이스 — 직접 연락 및 결제 계획 수립 필요")
        if any(a["type"] == "email_risk_signal" for a in alerts):
            recommendations.append("고객 이탈/해지 신호 감지 — 고객 성공팀 개입 권장")

        return {
            "expert": self.name,
            "revenue_health_score": revenue_health_score,
            "at_risk_revenue": at_risk_revenue,
            "alerts": alerts,
            "recommendations": recommendations,
            "alert_count": len(alerts),
        }

    def format_digest(self, results: dict) -> str:
        lines = [
            f"💰 **{self.name}** — 매출 보호 리포트",
            f"   매출 건강 점수: {results['revenue_health_score']:.0f}/100",
            f"   위험 매출: ${results['at_risk_revenue']:,.0f}",
            f"   알림 수: {results['alert_count']}건",
        ]
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
