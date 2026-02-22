#!/usr/bin/env python3
"""
classifier.py - 긴급 이메일 AI 분류기

TF-IDF + LogisticRegression 기반 긴급/비긴급 이메일 분류.
초기 학습 데이터는 키워드 기반 라벨링으로 부트스트랩.
poc/vectors/excluded_ids.json의 발신자는 자동 제외(노이즈 필터).
"""

import json
import os
import pickle
import re
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

# ── 경로 설정 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # workspace root
MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
EXCLUDED_IDS_PATH = BASE_DIR / "poc" / "vectors" / "excluded_ids.json"

# ── 키워드 기반 부트스트랩 학습 데이터 ─────────────────────
URGENT_KEYWORDS = [
    # 영어
    "urgent", "immediate", "asap", "critical", "emergency",
    "action required", "password reset", "security alert",
    "unauthorized access", "failed login", "account suspended",
    "verification required", "billing issue", "payment failed",
    "data breach", "compromise", "suspicious activity",
    "deadline today", "expires today", "final notice",
    # 한국어
    "긴급", "즉시", "보안 경고", "비밀번호 변경", "로그인 시도",
    "인증코드", "계정 정지", "결제 실패", "승인 필요",
    "마감", "최종 통보", "경고", "비인가 접근", "데이터 유출",
]

NOT_URGENT_KEYWORDS = [
    "newsletter", "digest", "weekly", "monthly", "update",
    "unsubscribe", "promotion", "deal", "offer", "sale",
    "notification preference", "no action needed",
    "뉴스레터", "주간", "월간", "프로모션", "할인", "광고",
]

# 부트스트랩 학습 데이터 (긴급)
BOOTSTRAP_URGENT = [
    "Urgent: Your account has been compromised, reset your password immediately",
    "SECURITY ALERT: Unauthorized login attempt detected on your account",
    "Action Required: Payment failed, update billing info now",
    "Critical: Server downtime affecting production systems",
    "ASAP: Contract deadline is today, signature needed",
    "Emergency: Data breach detected in customer database",
    "Your verification code expires in 5 minutes",
    "Final Notice: Account will be suspended in 24 hours",
    "Suspicious activity detected on your account",
    "긴급: 비밀번호 변경이 필요합니다",
    "보안 경고: 비인가 로그인 시도가 감지되었습니다",
    "즉시 조치 필요: 결제가 실패했습니다",
    "인증코드: 123456 - 5분 내 입력하세요",
    "계정 정지 경고: 24시간 내 조치 필요",
    "마감 임박: 오늘까지 서류 제출 필요",
    "Critical system alert: database connection failed",
    "Immediate action: your domain expires tomorrow",
    "Password reset requested - if not you, contact support immediately",
    "Failed login attempts from unknown IP address",
    "Urgent meeting rescheduled to today 3PM",
]

# 부트스트랩 학습 데이터 (비긴급)
BOOTSTRAP_NOT_URGENT = [
    "Weekly Newsletter: Top stories this week",
    "Your monthly statement is ready to view",
    "New features available in your dashboard",
    "Promotion: 50% off this weekend only",
    "Digest: 5 new posts in your feed",
    "Thank you for your purchase - order confirmation",
    "Invitation: Join us for a webinar next month",
    "Your subscription has been renewed successfully",
    "Newsletter: Industry trends and insights",
    "Update: We've updated our privacy policy",
    "주간 뉴스레터: 이번 주 주요 소식",
    "월간 리포트가 준비되었습니다",
    "프로모션: 이번 주말 50% 할인",
    "구독이 성공적으로 갱신되었습니다",
    "새로운 기능이 추가되었습니다",
    "Welcome to our community!",
    "Your order has been shipped",
    "Reminder: Upcoming event next week",
    "Tips and tricks for better productivity",
    "Check out what's new this month",
]


def _load_excluded_ids() -> set:
    """poc/vectors/excluded_ids.json에서 제외 목록 로드."""
    try:
        with open(EXCLUDED_IDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 리스트 또는 딕셔너리 형태 모두 지원
            if isinstance(data, list):
                return set(data)
            elif isinstance(data, dict):
                return set(data.keys())
            return set()
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _extract_text(email_dict: dict) -> str:
    """이메일 딕셔너리에서 분류용 텍스트 추출."""
    parts = []

    # 헤더 기반 (Gmail API 원시 형태)
    headers = email_dict.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers}

    subject = email_dict.get("subject") or header_map.get("subject", "")
    snippet = email_dict.get("snippet", "")
    body = email_dict.get("body", "")

    parts.append(subject)
    parts.append(snippet)
    if body:
        parts.append(body)

    return " ".join(parts).strip()


def _extract_sender(email_dict: dict) -> str:
    """이메일 딕셔너리에서 발신자 추출."""
    headers = email_dict.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers}
    return email_dict.get("from") or header_map.get("from", "")


def _keyword_score(text: str) -> Tuple[int, list]:
    """키워드 매칭 점수 및 매칭된 키워드 반환."""
    text_lower = text.lower()
    matched = []
    for kw in URGENT_KEYWORDS:
        if kw.lower() in text_lower:
            matched.append(kw)
    return len(matched), matched


def _build_bootstrap_model() -> Pipeline:
    """키워드 부트스트랩 데이터로 초기 모델 학습."""
    texts = BOOTSTRAP_URGENT + BOOTSTRAP_NOT_URGENT
    labels = [1] * len(BOOTSTRAP_URGENT) + [0] * len(BOOTSTRAP_NOT_URGENT)

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42,
        )),
    ])

    pipeline.fit(texts, labels)
    return pipeline


def load_model() -> Pipeline:
    """모델 로드. 없으면 부트스트랩 모델 생성 및 저장."""
    if MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                return pickle.load(f)
        except Exception:
            pass

    model = _build_bootstrap_model()
    save_model(model)
    return model


def save_model(model: Pipeline) -> None:
    """모델을 pkl로 저장."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)


def classify(email_dict: dict, model: Optional[Pipeline] = None) -> Tuple[bool, float, str]:
    """
    이메일을 긴급/비긴급으로 분류.

    Args:
        email_dict: Gmail API 형태의 이메일 딕셔너리
        model: 사전 로드된 모델 (없으면 자동 로드)

    Returns:
        (is_urgent, confidence, reason)
        - is_urgent: 긴급 여부
        - confidence: 0.0 ~ 1.0 신뢰도
        - reason: 분류 사유 설명
    """
    # 노이즈 필터: 제외 발신자 체크
    sender = _extract_sender(email_dict)
    excluded = _load_excluded_ids()

    # excluded_ids.json이 숫자 ID 리스트인 경우
    email_id = email_dict.get("id", "")
    sender_lower = sender.lower()

    # 발신자 도메인으로도 체크
    sender_domain = ""
    if "@" in sender:
        match = re.search(r"@([\w.-]+)", sender)
        if match:
            sender_domain = match.group(1).lower()

    # 제외 대상이면 비긴급으로 처리
    for ex in excluded:
        ex_str = str(ex).lower()
        if ex_str in sender_lower or ex_str == sender_domain:
            return (False, 0.0, f"노이즈 필터 제외 발신자: {sender}")

    # 텍스트 추출
    text = _extract_text(email_dict)
    if not text.strip():
        return (False, 0.0, "이메일 본문 없음")

    # ML 모델 분류
    if model is None:
        model = load_model()

    proba = model.predict_proba([text])[0]
    urgent_prob = proba[1] if len(proba) > 1 else proba[0]

    # 키워드 보강: 키워드 매칭 점수로 신뢰도 보정
    kw_score, matched_keywords = _keyword_score(text)
    if kw_score > 0:
        # 키워드 매칭 시 신뢰도 부스트 (최대 0.15)
        boost = min(kw_score * 0.05, 0.15)
        urgent_prob = min(urgent_prob + boost, 1.0)

    is_urgent = urgent_prob >= 0.5

    # 사유 생성
    reasons = []
    if matched_keywords:
        reasons.append(f"키워드 매칭: {', '.join(matched_keywords[:5])}")
    if urgent_prob >= 0.8:
        reasons.append("ML 모델 고신뢰 분류")
    elif urgent_prob >= 0.5:
        reasons.append("ML 모델 분류")

    reason = " | ".join(reasons) if reasons else ("비긴급 판단" if not is_urgent else "ML 모델 분류")

    return (is_urgent, float(urgent_prob), reason)


if __name__ == "__main__":
    # 간단 테스트
    test_emails = [
        {"subject": "URGENT: Password reset required immediately", "snippet": "Your account security has been compromised"},
        {"subject": "Weekly Newsletter", "snippet": "Check out the latest updates and deals"},
        {"subject": "긴급: 서버 장애 발생", "snippet": "프로덕션 서버에 심각한 장애가 발생했습니다"},
        {"subject": "프로모션: 이번 주 할인", "snippet": "다양한 상품을 할인된 가격에 만나보세요"},
    ]

    model = load_model()
    print("=" * 60)
    print("긴급 이메일 분류기 테스트")
    print("=" * 60)
    for email in test_emails:
        is_urgent, confidence, reason = classify(email, model)
        status = "🚨 긴급" if is_urgent else "✅ 일반"
        print(f"\n{status} | 신뢰도: {confidence:.0%}")
        print(f"  제목: {email['subject']}")
        print(f"  사유: {reason}")
