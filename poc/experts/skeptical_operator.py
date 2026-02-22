"""
SkepticalOperator — 회의적 운영 전문가.

낙관적 분석에 대한 균형추 역할. 비용 초과, 운영 병목,
실현 가능성 의문, 리소스 제약 등을 냉정하게 평가한다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_expert import BaseExpert


class SkepticalOperator(BaseExpert):
    name = "SkepticalOperator"
    description = "비용/운영 리스크를 냉정하게 평가하는 회의적 전문가"
    version = "1.0.0"

    RISK_KEYWORDS = [
        "delay", "bottleneck", "overbudget", "shortage", "constraint",
        "deadline", "escalation", "failure", "incident", "outage",
        "지연", "병목", "예산초과", "부족", "제약", "마감", "장애",
    ]

    COST_KEYWORDS = [
        "cost", "expense", "budget", "spend", "overhead", "burn rate",
        "비용", "경비", "예산", "지출", "소진율",
    ]

    def analyze(self, data: dict) -> dict:
        """
        운영 리스크 및 비용 분석.

        Parameters
        ----------
        data : dict
            keys: emails, operational_metrics, budgets, projects

        Returns
        -------
        dict
            operational_risk_score, red_flags[], cost_concerns[],
            bottlenecks[], recommendations[]
        """
        emails = data.get("emails", [])
        ops_metrics = data.get("operational_metrics", {})
        budgets = data.get("budgets", [])
        projects = data.get("projects", [])

        red_flags: List[Dict[str, Any]] = []
        cost_concerns: List[Dict[str, Any]] = []
        bottlenecks: List[Dict[str, Any]] = []

        # 1. 이메일에서 위험 신호 추출
        for email in emails:
            body = email.get("body", "") + " " + email.get("subject", "")
            risk_hits = self._extract_keywords(body, self.RISK_KEYWORDS)
            cost_hits = self._extract_keywords(body, self.COST_KEYWORDS)

            if risk_hits:
                red_flags.append({
                    "type": "operational_risk",
                    "source": email.get("from", "unknown"),
                    "keywords": risk_hits,
                    "impact_score": 7,
                    "urgency": 7,
                    "timestamp": email.get("timestamp"),
                })
            if cost_hits:
                cost_concerns.append({
                    "type": "cost_signal",
                    "source": email.get("from", "unknown"),
                    "keywords": cost_hits,
                    "impact_score": 6,
                    "urgency": 5,
                })

        # 2. 예산 초과 체크
        for budget in budgets:
            spent = budget.get("spent", 0)
            allocated = budget.get("allocated", 1)
            utilization = spent / max(allocated, 1)
            if utilization > 0.9:
                cost_concerns.append({
                    "type": "budget_overrun",
                    "department": budget.get("department", "unknown"),
                    "utilization_pct": utilization * 100,
                    "impact_score": 8,
                    "urgency": 8,
                })

        # 3. 프로젝트 지연 감지
        for proj in projects:
            if proj.get("status") == "delayed":
                bottlenecks.append({
                    "type": "project_delay",
                    "project": proj.get("name"),
                    "delay_days": proj.get("delay_days", 0),
                    "impact_score": 7,
                    "urgency": 6,
                })
            if proj.get("resource_shortage", False):
                bottlenecks.append({
                    "type": "resource_shortage",
                    "project": proj.get("name"),
                    "impact_score": 6,
                    "urgency": 7,
                })

        # 4. 운영 리스크 점수 (높을수록 위험)
        total_issues = len(red_flags) + len(cost_concerns) + len(bottlenecks)
        operational_risk_score = self._safe_score(total_issues * 8, 0, 100)

        # 5. 권고
        recommendations = []
        if cost_concerns:
            recommendations.append(f"비용 경고 {len(cost_concerns)}건 — 예산 재검토 및 지출 동결 고려")
        if bottlenecks:
            recommendations.append(f"운영 병목 {len(bottlenecks)}건 — 리소스 재배분 또는 일정 조정 필요")
        if red_flags:
            recommendations.append(f"적색 경보 {len(red_flags)}건 — 경영진 보고 및 즉시 대응 필요")
        if not total_issues:
            recommendations.append("현재 주요 운영 리스크 없음 — 지속 모니터링 유지")

        return {
            "expert": self.name,
            "operational_risk_score": operational_risk_score,
            "red_flags": red_flags,
            "cost_concerns": cost_concerns,
            "bottlenecks": bottlenecks,
            "recommendations": recommendations,
            "total_issues": total_issues,
        }

    def format_digest(self, results: dict) -> str:
        lines = [
            f"🔍 **{self.name}** — 운영 리스크 리포트",
            f"   운영 리스크 점수: {results['operational_risk_score']:.0f}/100 (높을수록 위험)",
            f"   적색 경보: {len(results['red_flags'])}건",
            f"   비용 경고: {len(results['cost_concerns'])}건",
            f"   운영 병목: {len(results['bottlenecks'])}건",
        ]
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
