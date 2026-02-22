"""
ComplianceWatch — 규정 준수 모니터링 전문가.

이메일/문서에서 규정 위반 위험, 정책 위반, 법적 리스크를
감지하여 컴플라이언스 건강도를 유지한다.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .base_expert import BaseExpert


class ComplianceWatch(BaseExpert):
    name = "ComplianceWatch"
    description = "규정 준수 모니터링, 리스크 감지, 정책 위반 알림 전문가"
    version = "1.0.0"

    # 규정/법률 키워드
    REGULATION_KEYWORDS = [
        "gdpr", "hipaa", "sox", "pci", "ccpa", "ferpa",
        "regulation", "compliance", "audit", "inspection",
        "개인정보", "정보보호", "규정", "감사", "점검", "인증",
    ]

    # 위험 행위 키워드
    RISK_KEYWORDS = [
        "confidential", "secret", "restricted", "nda",
        "unauthorized", "breach", "leak", "violation",
        "insider", "conflict of interest", "bribe", "kickback",
        "기밀", "비밀", "제한", "비인가", "유출", "위반",
        "내부자", "이해충돌", "뇌물",
    ]

    # 정책 위반 패턴
    POLICY_VIOLATION_PATTERNS = [
        "without approval", "bypassed", "ignored policy",
        "non-compliant", "failed to report", "unreported",
        "미승인", "정책무시", "미보고", "부적합",
    ]

    # 데이터 처리 키워드
    DATA_HANDLING_KEYWORDS = [
        "personal data", "sensitive data", "pii", "phi",
        "data transfer", "third party", "external sharing",
        "개인데이터", "민감정보", "데이터이전", "외부공유",
    ]

    SEVERITY_LEVELS = {
        "critical": 10,
        "high": 8,
        "medium": 5,
        "low": 3,
        "info": 1,
    }

    def analyze(self, data: dict) -> dict:
        """
        컴플라이언스 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails, documents, policies, audit_logs

        Returns
        -------
        dict
            risk_items[], compliance_score, policy_violations[], recommendations[]
        """
        emails = data.get("emails", [])
        documents = data.get("documents", [])
        policies = data.get("policies", [])
        audit_logs = data.get("audit_logs", [])

        risk_items: List[Dict[str, Any]] = []
        policy_violations: List[Dict[str, Any]] = []

        # 1. 이메일/문서 스캔
        all_sources = []
        for email in emails:
            text = email.get("body", "") + " " + email.get("subject", "")
            all_sources.append({
                "text": text,
                "type": "email",
                "from": email.get("from", "unknown"),
                "to": email.get("to", []),
                "timestamp": email.get("timestamp"),
            })
        for doc in documents:
            text = doc.get("content", "") + " " + doc.get("title", "")
            all_sources.append({
                "text": text,
                "type": "document",
                "from": doc.get("author", "unknown"),
                "to": [],
                "timestamp": doc.get("timestamp"),
            })

        for source in all_sources:
            text = source["text"]

            # 규정 관련 감지
            reg_hits = self._extract_keywords(text, self.REGULATION_KEYWORDS)
            risk_hits = self._extract_keywords(text, self.RISK_KEYWORDS)
            policy_hits = self._extract_keywords(text, self.POLICY_VIOLATION_PATTERNS)
            data_hits = self._extract_keywords(text, self.DATA_HANDLING_KEYWORDS)

            # 위험 항목 생성
            if risk_hits:
                severity = "critical" if any(
                    k in ["breach", "leak", "유출", "unauthorized", "비인가"]
                    for k in risk_hits
                ) else "high"
                risk_items.append({
                    "type": "security_risk",
                    "severity": severity,
                    "source_type": source["type"],
                    "from": source["from"],
                    "keywords": risk_hits,
                    "snippet": text[:200],
                    "impact_score": self.SEVERITY_LEVELS[severity],
                    "urgency": 9 if severity == "critical" else 7,
                    "timestamp": source["timestamp"],
                })

            # 정책 위반 감지
            if policy_hits:
                policy_violations.append({
                    "type": "policy_violation",
                    "severity": "high",
                    "source_type": source["type"],
                    "from": source["from"],
                    "patterns": policy_hits,
                    "snippet": text[:200],
                    "impact_score": 8,
                    "urgency": 8,
                    "timestamp": source["timestamp"],
                })

            # 데이터 처리 위험
            if data_hits and not reg_hits:
                # 데이터 관련 언급이 있지만 규정 준수 맥락이 아닌 경우
                risk_items.append({
                    "type": "data_handling_risk",
                    "severity": "medium",
                    "source_type": source["type"],
                    "from": source["from"],
                    "keywords": data_hits,
                    "snippet": text[:200],
                    "impact_score": 5,
                    "urgency": 5,
                    "timestamp": source["timestamp"],
                })

        # 2. 감사 로그 분석
        for log in audit_logs:
            if log.get("result") == "failed":
                risk_items.append({
                    "type": "audit_failure",
                    "severity": "high",
                    "action": log.get("action"),
                    "user": log.get("user"),
                    "impact_score": 8,
                    "urgency": 7,
                    "timestamp": log.get("timestamp"),
                })
            if log.get("anomaly", False):
                risk_items.append({
                    "type": "audit_anomaly",
                    "severity": "medium",
                    "action": log.get("action"),
                    "user": log.get("user"),
                    "details": log.get("details", ""),
                    "impact_score": 6,
                    "urgency": 6,
                    "timestamp": log.get("timestamp"),
                })

        # 3. 정책 커버리지 확인
        policy_names = {p.get("name", "").lower() for p in policies}
        essential_policies = [
            "data protection", "acceptable use", "incident response",
            "access control", "data retention", "privacy",
        ]
        missing_policies = [
            p for p in essential_policies if p not in policy_names
        ]

        # 4. 컴플라이언스 점수 계산
        base_score = 100.0
        critical_count = sum(1 for r in risk_items if r.get("severity") == "critical")
        high_count = sum(1 for r in risk_items if r.get("severity") == "high")
        medium_count = sum(1 for r in risk_items if r.get("severity") == "medium")

        penalty = (
            critical_count * 20
            + high_count * 10
            + medium_count * 5
            + len(policy_violations) * 12
            + len(missing_policies) * 8
        )
        compliance_score = self._safe_score(base_score - penalty)

        # 5. 권고
        recommendations = []
        if critical_count:
            recommendations.append(
                f"🚨 심각 위험 {critical_count}건 — 즉시 조사 및 대응 필요"
            )
        if policy_violations:
            recommendations.append(
                f"정책 위반 {len(policy_violations)}건 — 관련자 교육 및 시정 조치"
            )
        if missing_policies:
            recommendations.append(
                f"필수 정책 미비: {', '.join(missing_policies)} — 정책 수립 필요"
            )
        if high_count:
            recommendations.append(f"고위험 항목 {high_count}건 — 48시간 내 검토 필요")
        if not risk_items and not policy_violations:
            recommendations.append("현재 컴플라이언스 이슈 없음 — 정기 모니터링 유지")

        # 정렬
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        risk_items.sort(key=lambda x: severity_order.get(x.get("severity", "info"), 5))

        return {
            "expert": self.name,
            "risk_items": risk_items,
            "compliance_score": compliance_score,
            "policy_violations": policy_violations,
            "missing_policies": missing_policies,
            "severity_summary": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
            },
            "recommendations": recommendations,
        }

    def format_digest(self, results: dict) -> str:
        ss = results["severity_summary"]
        lines = [
            f"🛡️ **{self.name}** — 컴플라이언스 리포트",
            f"   컴플라이언스 점수: {results['compliance_score']:.0f}/100",
            f"   위험 항목: 심각 {ss['critical']}건 | 높음 {ss['high']}건 | 중간 {ss['medium']}건",
            f"   정책 위반: {len(results['policy_violations'])}건",
        ]
        if results.get("missing_policies"):
            lines.append(f"   ❌ 미비 정책: {', '.join(results['missing_policies'])}")
        if results.get("risk_items"):
            lines.append("   ⚠️ 주요 위험:")
            for r in results["risk_items"][:3]:
                lines.append(
                    f"      • [{r['severity'].upper()}] {r['type']} — {r.get('from', 'N/A')}"
                )
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
