#!/usr/bin/env python3
"""
retrain.py - 긴급 이메일 분류기 재학습

feedback_store의 피드백 데이터 + 부트스트랩 데이터로 모델을 재학습.
학습 결과를 poc/urgent/model.pkl에 저장하고 성능 리포트를 출력.

사용법:
    python3 poc/urgent/retrain.py
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from poc.urgent.classifier import (
    BOOTSTRAP_URGENT,
    BOOTSTRAP_NOT_URGENT,
    save_model,
    MODEL_PATH,
)
from poc.urgent.feedback_store import get_training_data, get_feedback_count

KST = timezone(timedelta(hours=9))


def retrain(min_feedback: int = 5, include_bootstrap: bool = True) -> dict:
    """
    모델 재학습 실행.

    Args:
        min_feedback: 최소 피드백 수 (이하면 부트스트랩만 사용)
        include_bootstrap: 부트스트랩 데이터 포함 여부

    Returns:
        학습 결과 리포트 딕셔너리
    """
    report = {
        "timestamp": datetime.now(KST).isoformat(),
        "feedback_stats": {},
        "training_samples": 0,
        "performance": {},
        "model_path": str(MODEL_PATH),
    }

    # 1. 피드백 데이터 로드
    print("=" * 60)
    print("🔄 긴급 이메일 분류기 재학습")
    print("=" * 60)

    feedback_stats = get_feedback_count()
    report["feedback_stats"] = feedback_stats
    print(f"\n📊 피드백 통계:")
    print(f"  총 피드백: {feedback_stats['total']}건")
    print(f"  정확도: {feedback_stats['accuracy']:.1%}")
    print(f"  긴급: {feedback_stats['urgent_count']}건 | 비긴급: {feedback_stats['not_urgent_count']}건")

    X_feedback, y_feedback = get_training_data()
    print(f"\n📥 피드백 학습 데이터: {len(X_feedback)}건")

    # 2. 학습 데이터 구성
    X_train = []
    y_train = []

    if include_bootstrap:
        X_train.extend(BOOTSTRAP_URGENT)
        y_train.extend([1] * len(BOOTSTRAP_URGENT))
        X_train.extend(BOOTSTRAP_NOT_URGENT)
        y_train.extend([0] * len(BOOTSTRAP_NOT_URGENT))
        print(f"📦 부트스트랩 데이터: {len(BOOTSTRAP_URGENT) + len(BOOTSTRAP_NOT_URGENT)}건")

    if len(X_feedback) >= min_feedback:
        # 피드백 데이터에 가중치 부여 (최신 데이터 2x)
        X_train.extend(X_feedback)
        y_train.extend(y_feedback)
        # 피드백 데이터 복제로 가중치 효과
        X_train.extend(X_feedback)
        y_train.extend(y_feedback)
        print(f"✅ 피드백 데이터 포함 (2x 가중치)")
    elif len(X_feedback) > 0:
        X_train.extend(X_feedback)
        y_train.extend(y_feedback)
        print(f"⚠️  피드백 {len(X_feedback)}건 (최소 {min_feedback}건 미만, 1x 가중치)")
    else:
        print("ℹ️  피드백 데이터 없음, 부트스트랩만 사용")

    report["training_samples"] = len(X_train)
    print(f"\n📊 총 학습 데이터: {len(X_train)}건")

    # 3. 모델 학습
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

    X_arr = np.array(X_train)
    y_arr = np.array(y_train)

    # 4. 교차 검증 (충분한 데이터가 있을 때)
    n_splits = min(5, min(np.sum(y_arr == 0), np.sum(y_arr == 1)))
    if n_splits >= 2:
        print(f"\n🔍 {n_splits}-Fold 교차 검증...")
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
        scores = cross_val_score(pipeline, X_arr, y_arr, cv=cv, scoring="f1")
        report["performance"]["cv_f1_mean"] = float(np.mean(scores))
        report["performance"]["cv_f1_std"] = float(np.std(scores))
        print(f"  F1 Score: {np.mean(scores):.3f} (±{np.std(scores):.3f})")
    else:
        print("\n⚠️  데이터 부족으로 교차 검증 스킵")

    # 5. 전체 데이터로 최종 학습
    pipeline.fit(X_arr, y_arr)

    # 학습 데이터 리포트
    y_pred = pipeline.predict(X_arr)
    train_report = classification_report(
        y_arr, y_pred,
        target_names=["비긴급", "긴급"],
        output_dict=True,
    )
    report["performance"]["train_report"] = train_report

    print("\n📋 학습 데이터 성능:")
    print(classification_report(
        y_arr, y_pred,
        target_names=["비긴급", "긴급"],
    ))

    # 6. 모델 저장
    save_model(pipeline)
    print(f"💾 모델 저장: {MODEL_PATH}")
    print(f"   크기: {MODEL_PATH.stat().st_size / 1024:.1f} KB")

    # 7. TF-IDF 상위 특성 출력
    tfidf = pipeline.named_steps["tfidf"]
    clf = pipeline.named_steps["clf"]
    feature_names = tfidf.get_feature_names_out()
    coefs = clf.coef_[0]

    top_urgent_idx = np.argsort(coefs)[-10:][::-1]
    top_not_urgent_idx = np.argsort(coefs)[:10]

    print("\n🔑 긴급 판단 주요 특성 (Top 10):")
    for idx in top_urgent_idx:
        print(f"  + {feature_names[idx]}: {coefs[idx]:.3f}")

    print("\n🔑 비긴급 판단 주요 특성 (Top 10):")
    for idx in top_not_urgent_idx:
        print(f"  - {feature_names[idx]}: {coefs[idx]:.3f}")

    print("\n✅ 재학습 완료")
    return report


if __name__ == "__main__":
    retrain()
