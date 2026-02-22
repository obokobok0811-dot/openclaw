#!/usr/bin/env python3
"""
alert_queue.py - 긴급 이메일 알림 큐

시간대 게이트 밖에서 감지된 긴급 이메일을 큐에 저장하고,
허용 시간대에 일괄 Telegram 전송.

DB: poc/urgent/alert_queue.db
스키마: queued_alerts(id, email_id, subject, sender, reason, confidence,
                       detected_at, sent_at NULL)
"""

import json
import sqlite3
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

KST = timezone(timedelta(hours=9))
DB_PATH = Path(__file__).resolve().parent / "alert_queue.db"
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # workspace root
TELEGRAM_CREDS_PATH = BASE_DIR / "credentials" / "telegram_bot.json"
TELEGRAM_PAIRING_PATH = BASE_DIR / "credentials" / "telegram_pairing.json"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS queued_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id TEXT NOT NULL UNIQUE,
    subject TEXT,
    sender TEXT,
    reason TEXT,
    confidence REAL,
    detected_at TEXT NOT NULL,
    sent_at TEXT
)
"""

CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_queued_unsent ON queued_alerts(sent_at)
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


def _load_telegram_config() -> dict:
    """Telegram 봇 토큰과 채팅 ID 로드."""
    config = {}

    try:
        with open(TELEGRAM_CREDS_PATH, "r") as f:
            bot_data = json.load(f)
            config["bot_token"] = bot_data.get("bot_token", "")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Telegram 봇 설정 로드 실패: {e}") from e

    try:
        with open(TELEGRAM_PAIRING_PATH, "r") as f:
            pairing_data = json.load(f)
            config["chat_id"] = pairing_data.get("chat_id", "")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise RuntimeError(f"Telegram 페어링 설정 로드 실패: {e}") from e

    if not config.get("bot_token") or not config.get("chat_id"):
        raise RuntimeError("Telegram bot_token 또는 chat_id 미설정")

    return config


def _send_telegram(message: str) -> bool:
    """Telegram 메시지 전송."""
    try:
        config = _load_telegram_config()
        url = f"https://api.telegram.org/bot{config['bot_token']}/sendMessage"
        payload = {
            "chat_id": config["chat_id"],
            "text": message,
            "parse_mode": "HTML",
        }
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[alert_queue] Telegram 전송 실패: {e}")
        return False


def _format_alert(subject: str, sender: str, confidence: float, reason: str) -> str:
    """알림 메시지 포맷."""
    return (
        f"🚨 긴급 이메일 감지\n"
        f"발신: {sender}\n"
        f"제목: {subject}\n"
        f"신뢰도: {confidence:.0%}\n"
        f"사유: {reason}"
    )


def enqueue(
    email_id: str,
    subject: str,
    sender: str,
    reason: str,
    confidence: float,
) -> Optional[int]:
    """
    긴급 이메일을 알림 큐에 추가.

    Args:
        email_id: 이메일 고유 ID
        subject: 이메일 제목
        sender: 발신자
        reason: 긴급 판단 사유
        confidence: 분류 신뢰도

    Returns:
        삽입된 레코드 ID (중복 시 None)
    """
    conn = _get_conn()
    try:
        now = datetime.now(KST).isoformat()
        cursor = conn.execute(
            "INSERT OR IGNORE INTO queued_alerts "
            "(email_id, subject, sender, reason, confidence, detected_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (email_id, subject, sender, reason, confidence, now),
        )
        conn.commit()
        return cursor.lastrowid if cursor.rowcount > 0 else None
    except sqlite3.Error as e:
        print(f"[alert_queue] 큐 저장 실패: {e}")
        return None
    finally:
        conn.close()


def send_immediate(
    email_id: str,
    subject: str,
    sender: str,
    reason: str,
    confidence: float,
) -> bool:
    """
    즉시 Telegram 알림 전송 (시간대 허용 시).

    전송 성공 시 DB에 sent_at 기록.
    """
    message = _format_alert(subject, sender, confidence, reason)
    success = _send_telegram(message)

    if success:
        # 보낸 기록 저장 (중복 방지용)
        conn = _get_conn()
        try:
            now = datetime.now(KST).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO queued_alerts "
                "(email_id, subject, sender, reason, confidence, detected_at, sent_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (email_id, subject, sender, reason, confidence, now, now),
            )
            conn.commit()
        finally:
            conn.close()

    return success


def flush_pending() -> int:
    """
    미전송 큐를 확인하고 Telegram으로 일괄 전송.

    Returns:
        전송 성공한 알림 수
    """
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT id, email_id, subject, sender, reason, confidence "
            "FROM queued_alerts WHERE sent_at IS NULL "
            "ORDER BY detected_at ASC"
        ).fetchall()

        if not rows:
            return 0

        sent_count = 0

        # 다수의 미전송 알림이 있으면 요약 헤더
        if len(rows) > 1:
            header = f"📬 대기 중이던 긴급 이메일 {len(rows)}건을 전달합니다.\n{'─' * 30}"
            _send_telegram(header)

        for row_id, email_id, subject, sender, reason, confidence in rows:
            message = _format_alert(subject, sender, confidence, reason)

            if _send_telegram(message):
                now = datetime.now(KST).isoformat()
                conn.execute(
                    "UPDATE queued_alerts SET sent_at = ? WHERE id = ?",
                    (now, row_id),
                )
                conn.commit()
                sent_count += 1

        return sent_count
    finally:
        conn.close()


def get_pending_count() -> int:
    """미전송 알림 수 조회."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM queued_alerts WHERE sent_at IS NULL"
        ).fetchone()
        return row[0]
    finally:
        conn.close()


def is_already_queued(email_id: str) -> bool:
    """이미 큐에 있는 이메일인지 확인."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM queued_alerts WHERE email_id = ?",
            (email_id,),
        ).fetchone()
        return row[0] > 0
    finally:
        conn.close()


if __name__ == "__main__":
    print("알림 큐 테스트")
    print("=" * 40)

    # 테스트 큐 추가
    rid = enqueue(
        email_id="test_alert_001",
        subject="긴급: 서버 다운",
        sender="devops@example.com",
        reason="키워드 매칭: 긴급, 서버",
        confidence=0.92,
    )
    print(f"큐 추가: ID={rid}")

    pending = get_pending_count()
    print(f"미전송 알림: {pending}건")
