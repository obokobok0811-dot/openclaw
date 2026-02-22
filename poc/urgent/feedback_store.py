#!/usr/bin/env python3
"""
feedback_store.py - 피드백 학습 루프

긴급 이메일 분류 결과에 대한 피드백을 SQLite에 저장하고,
재학습용 데이터를 추출하는 모듈.

DB: poc/urgent/feedback.db
스키마: feedback(id, email_id, predicted_urgent, actual_urgent, features_json, created_at)
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Optional

DB_PATH = Path(__file__).resolve().parent / "feedback.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL,
    predicted_urgent INTEGER NOT NULL,
    actual_urgent INTEGER NOT NULL,
    features_json TEXT,
    created_at TEXT NOT NULL
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_feedback_email_id ON feedback(email_id)
"""


def _get_conn() -> sqlite3.Connection:
    """DB 연결 생성 및 테이블 초기화."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(CREATE_TABLE_SQL)
    conn.execute(CREATE_INDEX_SQL)
    conn.commit()
    return conn


def record_feedback(
    email_id: str,
    predicted: bool,
    actual: bool,
    features: Optional[dict] = None,
) -> int:
    """
    분류 결과에 대한 피드백 기록.

    Args:
        email_id: 이메일 고유 ID
        predicted: 모델이 예측한 긴급 여부
        actual: 실제 긴급 여부 (사용자 피드백)
        features: 추가 특성 정보 (subject, sender 등)

    Returns:
        삽입된 레코드의 ID
    """
    conn = _get_conn()
    try:
        now = datetime.now(timezone.utc).isoformat()
        features_json = json.dumps(features, ensure_ascii=False) if features else None

        cursor = conn.execute(
            "INSERT INTO feedback (email_id, predicted_urgent, actual_urgent, features_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (email_id, int(predicted), int(actual), features_json, now),
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.Error as e:
        raise RuntimeError(f"피드백 저장 실패: {e}") from e
    finally:
        conn.close()


def get_training_data() -> Tuple[List[str], List[int]]:
    """
    재학습용 (X, y) 데이터 추출.

    features_json에서 텍스트를 복원하여 X로,
    actual_urgent를 y로 반환.

    Returns:
        (X, y) - X는 텍스트 리스트, y는 라벨 리스트 (1=긴급, 0=비긴급)
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT features_json, actual_urgent FROM feedback "
            "WHERE features_json IS NOT NULL "
            "ORDER BY created_at"
        ).fetchall()

        X, y = [], []
        for features_json, label in rows:
            try:
                features = json.loads(features_json)
            except (json.JSONDecodeError, TypeError):
                continue

            # 텍스트 복원: subject + snippet + body
            text_parts = []
            for key in ("subject", "snippet", "body", "text"):
                val = features.get(key, "")
                if val:
                    text_parts.append(str(val))

            text = " ".join(text_parts).strip()
            if text:
                X.append(text)
                y.append(int(label))

        return X, y
    finally:
        conn.close()


def get_feedback_count() -> dict:
    """피드백 통계 반환."""
    conn = _get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
        correct = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE predicted_urgent = actual_urgent"
        ).fetchone()[0]
        urgent_count = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE actual_urgent = 1"
        ).fetchone()[0]

        accuracy = correct / total if total > 0 else 0.0

        return {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "urgent_count": urgent_count,
            "not_urgent_count": total - urgent_count,
        }
    finally:
        conn.close()


def has_feedback_for(email_id: str) -> bool:
    """특정 이메일에 대한 피드백이 이미 존재하는지 확인."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM feedback WHERE email_id = ?",
            (email_id,),
        ).fetchone()
        return row[0] > 0
    finally:
        conn.close()


if __name__ == "__main__":
    # 테스트
    print("피드백 스토어 테스트")
    print("=" * 40)

    # 샘플 피드백 기록
    rid = record_feedback(
        email_id="test_001",
        predicted=True,
        actual=True,
        features={"subject": "URGENT: Server down", "snippet": "Production server is not responding"},
    )
    print(f"피드백 기록 ID: {rid}")

    rid = record_feedback(
        email_id="test_002",
        predicted=True,
        actual=False,
        features={"subject": "Weekly Newsletter", "snippet": "Check out new deals"},
    )
    print(f"피드백 기록 ID: {rid}")

    # 통계 확인
    stats = get_feedback_count()
    print(f"\n통계: {stats}")

    # 학습 데이터 추출
    X, y = get_training_data()
    print(f"학습 데이터: {len(X)} 샘플")
    for text, label in zip(X, y):
        print(f"  [{label}] {text[:60]}...")
