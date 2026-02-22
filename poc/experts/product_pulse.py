"""
ProductPulse — 제품/서비스 품질 모니터링 전문가.

사용자 피드백 분석, 기능 요청 추적, 제품 품질 이슈 감지를 통해
제품 건강도를 실시간으로 모니터링한다.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .base_expert import BaseExpert


class ProductPulse(BaseExpert):
    name = "ProductPulse"
    description = "제품/서비스 품질 모니터링 및 피드백 분석 전문가"
    version = "1.0.0"

    FEEDBACK_KEYWORDS = [
        "bug", "crash", "error", "broken", "slow", "laggy",
        "love", "great", "awesome", "perfect", "excellent",
        "hate", "terrible", "worst", "useless", "frustrating",
        "버그", "오류", "느림", "불편", "좋아", "최고", "최악", "불만",
    ]

    FEATURE_KEYWORDS = [
        "feature request", "wish", "would be nice", "should have",
        "need", "want", "missing", "add", "integrate",
        "기능 요청", "추가", "개선", "통합", "필요",
    ]

    PAIN_KEYWORDS = [
        "pain point", "frustration", "workaround", "difficult",
        "confusing", "complicated", "inconvenient",
        "불편", "어려움", "복잡", "우회",
    ]

    POSITIVE_KEYWORDS = {"love", "great", "awesome", "perfect", "excellent", "좋아", "최고"}
    NEGATIVE_KEYWORDS = {"bug", "crash", "error", "broken", "hate", "terrible", "worst",
                         "useless", "frustrating", "버그", "오류", "최악", "불만"}

    def analyze(self, data: dict) -> dict:
        """
        제품 관련 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails, crm_tickets, reviews, product_metrics

        Returns
        -------
        dict
            product_health_score, feature_requests[], pain_points[], recommendations[]
        """
        emails = data.get("emails", [])
        tickets = data.get("crm_tickets", [])
        reviews = data.get("reviews", [])
        metrics = data.get("product_metrics", {})

        feature_requests: List[Dict[str, Any]] = []
        pain_points: List[Dict[str, Any]] = []
        sentiment_scores: List[float] = []
        topic_counter: Counter = Counter()

        all_text_sources = []

        # 이메일 텍스트 수집
        for email in emails:
            text = email.get("body", "") + " " + email.get("subject", "")
            all_text_sources.append({"text": text, "source": "email",
                                      "from": email.get("from", "unknown"),
                                      "timestamp": email.get("timestamp")})

        # 티켓 텍스트 수집
        for ticket in tickets:
            text = ticket.get("description", "") + " " + ticket.get("title", "")
            all_text_sources.append({"text": text, "source": "ticket",
                                      "from": ticket.get("reporter", "unknown"),
                                      "timestamp": ticket.get("created_at")})

        # 리뷰 텍스트 수집
        for review in reviews:
            text = review.get("content", "")
            all_text_sources.append({"text": text, "source": "review",
                                      "from": review.get("author", "unknown"),
                                      "timestamp": review.get("timestamp")})

        # 텍스트 분석
        for item in all_text_sources:
            text = item["text"]

            # 감성 분석 (간이)
            pos = len(self._extract_keywords(text, list(self.POSITIVE_KEYWORDS)))
            neg = len(self._extract_keywords(text, list(self.NEGATIVE_KEYWORDS)))
            if pos + neg > 0:
                sentiment = (pos - neg) / (pos + neg)  # -1 ~ 1
                sentiment_scores.append(sentiment)

            # 기능 요청 감지
            feat_hits = self._extract_keywords(text, self.FEATURE_KEYWORDS)
            if feat_hits:
                feature_requests.append({
                    "source": item["source"],
                    "from": item["from"],
                    "keywords": feat_hits,
                    "snippet": text[:200],
                    "impact_score": 5,
                    "urgency": 4,
                    "timestamp": item["timestamp"],
                })
                for kw in feat_hits:
                    topic_counter[kw] += 1

            # 고통점 감지
            pain_hits = self._extract_keywords(text, self.PAIN_KEYWORDS)
            if pain_hits:
                pain_points.append({
                    "source": item["source"],
                    "from": item["from"],
                    "keywords": pain_hits,
                    "snippet": text[:200],
                    "impact_score": 6,
                    "urgency": 6,
                    "timestamp": item["timestamp"],
                })

        # 제품 건강 점수
        avg_sentiment = (sum(sentiment_scores) / len(sentiment_scores)) if sentiment_scores else 0.0
        sentiment_component = (avg_sentiment + 1) / 2 * 40  # 0~40

        bug_rate = metrics.get("bug_rate", 0)
        uptime = metrics.get("uptime_pct", 99.9)
        stability_component = max(0, (uptime - 95) / 5 * 30)  # 0~30
        pain_penalty = min(len(pain_points) * 3, 20)

        product_health_score = self._safe_score(
            sentiment_component + stability_component + 30 - pain_penalty
        )

        # 인기 기능 요청 Top5
        top_requests = topic_counter.most_common(5)

        # 권고
        recommendations = []
        if pain_points:
            recommendations.append(f"고객 고통점 {len(pain_points)}건 감지 — UX 개선 검토 필요")
        if feature_requests:
            recommendations.append(f"기능 요청 {len(feature_requests)}건 수집 — 제품 로드맵 반영 검토")
        if avg_sentiment < -0.3:
            recommendations.append("전반적 부정 감성 감지 — 긴급 품질 점검 필요")
        if bug_rate > 5:
            recommendations.append(f"버그 발생률 높음 ({bug_rate}/주) — QA 강화 권장")
        if top_requests:
            top_kw = top_requests[0][0]
            recommendations.append(f"가장 많이 요청된 기능: '{top_kw}' ({top_requests[0][1]}건)")

        return {
            "expert": self.name,
            "product_health_score": product_health_score,
            "feature_requests": feature_requests,
            "pain_points": pain_points,
            "avg_sentiment": round(avg_sentiment, 3),
            "top_feature_requests": [{"keyword": k, "count": c} for k, c in top_requests],
            "recommendations": recommendations,
        }

    def format_digest(self, results: dict) -> str:
        lines = [
            f"🛠️ **{self.name}** — 제품 건강 리포트",
            f"   제품 건강 점수: {results['product_health_score']:.0f}/100",
            f"   평균 감성: {results['avg_sentiment']:+.2f}",
            f"   기능 요청: {len(results['feature_requests'])}건",
            f"   고통점: {len(results['pain_points'])}건",
        ]
        if results.get("top_feature_requests"):
            lines.append("   🔝 인기 기능 요청:")
            for item in results["top_feature_requests"][:3]:
                lines.append(f"      • {item['keyword']} ({item['count']}건)")
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
