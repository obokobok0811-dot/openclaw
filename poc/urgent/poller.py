#!/usr/bin/env python3
"""
poller.py - 30분 폴링 서비스

Gmail API로 최근 30분 이메일을 체크하고,
노이즈 필터 → AI 분류기 → 시간대 게이트 → 알림/큐 파이프라인 실행.

사용법:
    python3 poc/urgent/poller.py

LaunchAgent로 30분 간격 자동 실행.
"""

import json
import os
import sys
import base64
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Google API
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 내부 모듈
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from poc.urgent.classifier import classify, load_model
from poc.urgent.time_gate import is_alert_allowed
from poc.urgent.alert_queue import enqueue, send_immediate, flush_pending, is_already_queued, get_pending_count

# ── 설정 ────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # workspace root
TOKEN_PATH = BASE_DIR / "credentials" / "token.json"
CLIENT_SECRET_PATH = BASE_DIR / "credentials" / "google_oauth_client.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# 처리 완료 ID 캐시 (SQLite 기반)
PROCESSED_DB_PATH = Path(__file__).resolve().parent / "processed.db"

LOG_PREFIX = "[urgent-poller]"


def _log(msg: str) -> None:
    """타임스탬프 로그 출력."""
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"{LOG_PREFIX} {now} {msg}")


def _get_gmail_service():
    """Gmail API 서비스 생성."""
    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        except Exception as e:
            _log(f"토큰 갱신 실패: {e}")
            raise

    if not creds or not creds.valid:
        raise RuntimeError(
            f"유효한 Gmail 토큰이 없습니다. {TOKEN_PATH}를 확인하세요."
        )

    return build("gmail", "v1", credentials=creds)


def _init_processed_db():
    """처리 완료 ID DB 초기화."""
    import sqlite3

    conn = sqlite3.connect(str(PROCESSED_DB_PATH))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS processed ("
        "  email_id TEXT PRIMARY KEY,"
        "  processed_at TEXT NOT NULL"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_processed_at ON processed(processed_at)"
    )
    conn.commit()
    return conn


def _is_processed(conn, email_id: str) -> bool:
    """이미 처리된 이메일인지 확인."""
    row = conn.execute(
        "SELECT 1 FROM processed WHERE email_id = ?", (email_id,)
    ).fetchone()
    return row is not None


def _mark_processed(conn, email_id: str) -> None:
    """이메일을 처리 완료로 마킹."""
    now = datetime.now(KST).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO processed (email_id, processed_at) VALUES (?, ?)",
        (email_id, now),
    )
    conn.commit()


def _cleanup_old_processed(conn, days: int = 7) -> None:
    """오래된 처리 완료 기록 정리."""
    cutoff = (datetime.now(KST) - timedelta(days=days)).isoformat()
    conn.execute("DELETE FROM processed WHERE processed_at < ?", (cutoff,))
    conn.commit()


def _extract_email_info(msg: dict) -> dict:
    """Gmail API 메시지에서 필요한 정보 추출."""
    headers = msg.get("payload", {}).get("headers", [])
    header_map = {h["name"].lower(): h["value"] for h in headers}

    sender = header_map.get("from", "")
    subject = header_map.get("subject", "")
    snippet = msg.get("snippet", "")
    email_id = msg.get("id", "")

    return {
        "id": email_id,
        "from": sender,
        "subject": subject,
        "snippet": snippet,
        "payload": msg.get("payload", {}),
    }


def _fetch_recent_emails(service, minutes: int = 30) -> list:
    """최근 N분 이내 이메일 목록 조회."""
    # Gmail API는 epoch seconds 기반 after: 쿼리 지원
    after_epoch = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
    query = f"after:{after_epoch}"

    try:
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=50,
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return []

        # 각 메시지의 상세 정보 조회
        detailed = []
        for msg_ref in messages:
            try:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_ref["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"],
                ).execute()
                detailed.append(msg)
            except Exception as e:
                _log(f"메시지 조회 실패 ({msg_ref['id']}): {e}")
                continue

        return detailed

    except Exception as e:
        _log(f"이메일 목록 조회 실패: {e}")
        return []


def poll() -> dict:
    """
    메인 폴링 루프 (1회 실행).

    Returns:
        결과 요약 딕셔너리
    """
    results = {
        "checked": 0,
        "skipped": 0,
        "urgent_found": 0,
        "alerts_sent": 0,
        "alerts_queued": 0,
        "queue_flushed": 0,
        "errors": [],
    }

    _log("폴링 시작")

    # 1. Gmail 서비스 초기화
    try:
        service = _get_gmail_service()
    except Exception as e:
        _log(f"Gmail 서비스 초기화 실패: {e}")
        results["errors"].append(str(e))
        return results

    # 2. 처리 완료 DB
    import sqlite3
    proc_conn = _init_processed_db()

    # 3. 오래된 처리 기록 정리
    _cleanup_old_processed(proc_conn)

    # 4. 모델 로드
    try:
        model = load_model()
    except Exception as e:
        _log(f"모델 로드 실패: {e}")
        results["errors"].append(str(e))
        proc_conn.close()
        return results

    # 5. 최근 이메일 조회
    emails = _fetch_recent_emails(service, minutes=35)  # 여유분 5분
    results["checked"] = len(emails)
    _log(f"조회된 이메일: {len(emails)}건")

    # 6. 먼저 대기 큐 flush (시간대 허용 시)
    if is_alert_allowed():
        flushed = flush_pending()
        results["queue_flushed"] = flushed
        if flushed > 0:
            _log(f"대기 큐 전송: {flushed}건")

    # 7. 각 이메일 처리
    for msg in emails:
        email_info = _extract_email_info(msg)
        email_id = email_info["id"]

        # 중복 방지
        if _is_processed(proc_conn, email_id) or is_already_queued(email_id):
            results["skipped"] += 1
            continue

        # 분류
        try:
            is_urgent, confidence, reason = classify(email_info, model)
        except Exception as e:
            _log(f"분류 실패 ({email_id}): {e}")
            results["errors"].append(f"classify: {e}")
            continue

        # 처리 완료 마킹
        _mark_processed(proc_conn, email_id)

        if not is_urgent:
            continue

        results["urgent_found"] += 1
        _log(f"긴급 감지: [{confidence:.0%}] {email_info['subject'][:50]}")

        # 시간대 게이트
        sender = email_info.get("from", "")
        subject = email_info.get("subject", "")

        if is_alert_allowed():
            # 즉시 전송
            success = send_immediate(email_id, subject, sender, reason, confidence)
            if success:
                results["alerts_sent"] += 1
                _log(f"알림 전송 완료: {subject[:40]}")
            else:
                # 전송 실패 시 큐에 저장
                enqueue(email_id, subject, sender, reason, confidence)
                results["alerts_queued"] += 1
        else:
            # 큐에 저장
            enqueue(email_id, subject, sender, reason, confidence)
            results["alerts_queued"] += 1
            _log(f"알림 큐 저장 (시간대 외): {subject[:40]}")

    proc_conn.close()

    # 결과 요약
    _log(
        f"폴링 완료 | 확인: {results['checked']} | "
        f"스킵: {results['skipped']} | "
        f"긴급: {results['urgent_found']} | "
        f"전송: {results['alerts_sent']} | "
        f"큐: {results['alerts_queued']} | "
        f"큐플러시: {results['queue_flushed']}"
    )

    return results


if __name__ == "__main__":
    try:
        result = poll()
        if result["errors"]:
            _log(f"에러 {len(result['errors'])}건 발생")
            for err in result["errors"]:
                _log(f"  ⚠️  {err}")
            sys.exit(1)
    except Exception as e:
        _log(f"치명적 오류: {e}")
        traceback.print_exc()
        sys.exit(1)
