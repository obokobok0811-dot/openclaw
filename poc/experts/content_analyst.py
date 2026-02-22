"""
ContentAnalyst — 콘텐츠 성과 분석 전문가.

콘텐츠 테마 추출, 트렌드 감지, 콘텐츠 갭 분석을 통해
마케팅 및 커뮤니케이션 전략을 지원한다.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from .base_expert import BaseExpert


class ContentAnalyst(BaseExpert):
    name = "ContentAnalyst"
    description = "콘텐츠 성과 분석, 트렌드 감지, 콘텐츠 갭 분석 전문가"
    version = "1.0.0"

    CONTENT_KEYWORDS = [
        "blog", "article", "video", "webinar", "podcast", "whitepaper",
        "case study", "newsletter", "social media", "campaign",
        "블로그", "기사", "영상", "웨비나", "팟캐스트", "뉴스레터",
        "캠페인", "소셜미디어", "사례연구",
    ]

    ENGAGEMENT_KEYWORDS = [
        "click", "open rate", "engagement", "share", "like",
        "comment", "subscribe", "download", "view",
        "클릭", "조회", "공유", "구독", "다운로드",
    ]

    TOPIC_INDICATORS = [
        "ai", "machine learning", "automation", "sustainability",
        "cloud", "security", "data", "analytics", "digital transformation",
        "인공지능", "자동화", "클라우드", "보안", "데이터", "디지털전환",
    ]

    def analyze(self, data: dict) -> dict:
        """
        콘텐츠 관련 데이터 분석.

        Parameters
        ----------
        data : dict
            keys: emails, documents, content_metrics, content_inventory

        Returns
        -------
        dict
            content_themes[], trending_topics[], content_gaps[], recommendations[]
        """
        emails = data.get("emails", [])
        documents = data.get("documents", [])
        content_metrics = data.get("content_metrics", [])
        inventory = data.get("content_inventory", [])

        theme_counter: Counter = Counter()
        topic_counter: Counter = Counter()
        engagement_signals: List[Dict[str, Any]] = []
        content_gaps: List[Dict[str, Any]] = []

        # 1. 이메일 + 문서에서 테마 추출
        all_texts = []
        for email in emails:
            all_texts.append(email.get("body", "") + " " + email.get("subject", ""))
        for doc in documents:
            all_texts.append(doc.get("content", "") + " " + doc.get("title", ""))

        for text in all_texts:
            content_hits = self._extract_keywords(text, self.CONTENT_KEYWORDS)
            topic_hits = self._extract_keywords(text, self.TOPIC_INDICATORS)
            engagement_hits = self._extract_keywords(text, self.ENGAGEMENT_KEYWORDS)

            for kw in content_hits:
                theme_counter[kw.lower()] += 1
            for kw in topic_hits:
                topic_counter[kw.lower()] += 1

            if engagement_hits:
                engagement_signals.append({
                    "keywords": engagement_hits,
                    "snippet": text[:150],
                })

        # 2. 콘텐츠 성과 분석
        high_performers = []
        low_performers = []
        for metric in content_metrics:
            score = metric.get("engagement_score", 0)
            if score >= 80:
                high_performers.append(metric)
            elif score <= 30:
                low_performers.append(metric)

        # 3. 트렌딩 토픽 (빈도 기반)
        trending_topics = [
            {"topic": topic, "mentions": count}
            for topic, count in topic_counter.most_common(10)
        ]

        # 4. 콘텐츠 갭 분석 — 많이 언급되지만 인벤토리에 없는 주제
        inventory_topics = set()
        for item in inventory:
            for tag in item.get("tags", []):
                inventory_topics.add(tag.lower())

        for topic, count in topic_counter.most_common(20):
            if topic not in inventory_topics and count >= 2:
                content_gaps.append({
                    "topic": topic,
                    "demand_mentions": count,
                    "has_content": False,
                    "impact_score": min(count * 2, 10),
                    "urgency": 5,
                })

        # 5. 테마 요약
        content_themes = [
            {"theme": theme, "frequency": freq}
            for theme, freq in theme_counter.most_common(10)
        ]

        # 6. 콘텐츠 건강 점수
        total_content = len(content_metrics) or 1
        high_ratio = len(high_performers) / total_content
        gap_penalty = min(len(content_gaps) * 5, 25)
        content_score = self._safe_score(high_ratio * 60 + 40 - gap_penalty)

        # 7. 권고
        recommendations = []
        if content_gaps:
            top_gap = content_gaps[0]
            recommendations.append(
                f"콘텐츠 갭 발견: '{top_gap['topic']}' — {top_gap['demand_mentions']}회 언급, 콘텐츠 제작 검토"
            )
        if low_performers:
            recommendations.append(f"저성과 콘텐츠 {len(low_performers)}건 — 개선 또는 폐기 검토")
        if trending_topics:
            recommendations.append(f"트렌딩 토픽: '{trending_topics[0]['topic']}' — 관련 콘텐츠 강화")
        if high_performers:
            recommendations.append(f"고성과 콘텐츠 {len(high_performers)}건 — 재활용/확장 전략 수립")

        return {
            "expert": self.name,
            "content_score": content_score,
            "content_themes": content_themes,
            "trending_topics": trending_topics,
            "content_gaps": content_gaps,
            "high_performers_count": len(high_performers),
            "low_performers_count": len(low_performers),
            "recommendations": recommendations,
        }

    def format_digest(self, results: dict) -> str:
        lines = [
            f"📝 **{self.name}** — 콘텐츠 분석 리포트",
            f"   콘텐츠 점수: {results['content_score']:.0f}/100",
            f"   고성과: {results['high_performers_count']}건 | 저성과: {results['low_performers_count']}건",
            f"   콘텐츠 갭: {len(results['content_gaps'])}건",
        ]
        if results.get("trending_topics"):
            lines.append("   🔥 트렌딩 토픽:")
            for t in results["trending_topics"][:3]:
                lines.append(f"      • {t['topic']} ({t['mentions']}회)")
        if results.get("content_gaps"):
            lines.append("   🕳️ 콘텐츠 갭:")
            for g in results["content_gaps"][:3]:
                lines.append(f"      • {g['topic']} (수요 {g['demand_mentions']}회)")
        if results.get("recommendations"):
            lines.append("   📌 권고:")
            for rec in results["recommendations"]:
                lines.append(f"      • {rec}")
        return "\n".join(lines)
