#!/usr/bin/env python3
"""
telegram_ingest.py - Telegram에서 URL 수신 시 자동 Knowledge Base ingest

Auto-post 모드: 확인 없이 URL을 바로 Knowledge API로 전송하여 처리합니다.

사용법:
    1. 독립 실행: python telegram_ingest.py
    2. 다른 Telegram bot 스크립트에서 import하여 사용

환경변수:
    KNOWLEDGE_API_URL: Knowledge API 엔드포인트 (기본: http://localhost:5001)
    TELEGRAM_BOT_TOKEN: Telegram Bot 토큰 (독립 실행 시 필요)
"""

import os
import re
import sys
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

try:
    import requests
except ImportError:
    requests = None
    logger.error("requests not installed. Install: pip install requests")

# === Configuration ===
KNOWLEDGE_API_URL = os.environ.get("KNOWLEDGE_API_URL", "http://localhost:5001")

# URL 추출 정규식
URL_PATTERN = re.compile(
    r"https?://[^\s<>\"'\]\)]+",
    re.IGNORECASE,
)

# 무시할 URL 패턴 (이미지, 비디오 등)
IGNORE_EXTENSIONS = frozenset([
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg",
    ".mp4", ".mov", ".avi", ".mkv",
    ".mp3", ".wav", ".ogg",
    ".pdf",  # PDF는 별도 처리 필요
    ".zip", ".tar", ".gz",
])


def extract_urls(text: str) -> list[str]:
    """
    텍스트에서 URL을 추출합니다.

    Args:
        text: 입력 텍스트

    Returns:
        추출된 URL 리스트 (중복 제거, 무시 확장자 필터링)
    """
    if not text:
        return []

    urls = URL_PATTERN.findall(text)

    # 필터링
    filtered = []
    seen = set()
    for url in urls:
        # 끝에 붙은 구두점 제거
        url = url.rstrip(".,;:!?")

        if url in seen:
            continue
        seen.add(url)

        # 무시할 확장자 체크
        lower_url = url.lower().split("?")[0]  # query string 제거
        if any(lower_url.endswith(ext) for ext in IGNORE_EXTENSIONS):
            continue

        filtered.append(url)

    return filtered


def ingest_url(url: str, api_url: Optional[str] = None) -> dict:
    """
    URL을 Knowledge API로 전송하여 ingest합니다.

    Args:
        url: ingest할 URL
        api_url: Knowledge API base URL

    Returns:
        API 응답 dict

    Raises:
        RuntimeError: requests 미설치 또는 API 오류
    """
    if requests is None:
        raise RuntimeError("requests library required")

    base = api_url or KNOWLEDGE_API_URL
    endpoint = f"{base}/ingest"

    try:
        resp = requests.post(
            endpoint,
            json={"url": url},
            timeout=30,
        )

        if resp.status_code == 200:
            result = resp.json()
            logger.info(
                f"Ingested: {result.get('title', 'N/A')} "
                f"(id={result.get('article_id')}, entities={len(result.get('entities', {}).get('persons', []))} persons)"
            )
            return result
        else:
            error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"error": resp.text}
            logger.warning(f"Ingest failed ({resp.status_code}): {error}")
            return {"status": "error", "code": resp.status_code, **error}

    except requests.RequestException as e:
        logger.error(f"API request failed: {e}")
        return {"status": "error", "error": str(e)}


def process_message(text: str, api_url: Optional[str] = None) -> list[dict]:
    """
    메시지에서 URL을 추출하고 각각 ingest합니다.
    Auto-post 모드: 확인 없이 바로 처리.

    Args:
        text: 메시지 텍스트
        api_url: Knowledge API base URL

    Returns:
        각 URL의 ingest 결과 리스트
    """
    urls = extract_urls(text)
    if not urls:
        return []

    results = []
    for url in urls:
        logger.info(f"Auto-ingesting: {url}")
        result = ingest_url(url, api_url)
        result["source_url"] = url
        results.append(result)

    return results


def format_result(result: dict) -> str:
    """ingest 결과를 사람이 읽기 좋은 형식으로 포맷합니다."""
    if result.get("status") == "ok":
        title = result.get("title", "N/A")
        article_id = result.get("article_id", "?")
        entities = result.get("entities", {})
        entity_summary = []
        for key, values in entities.items():
            if values:
                entity_summary.append(f"{key}: {', '.join(values[:3])}")
        entity_str = " | ".join(entity_summary) if entity_summary else "없음"
        return f"✅ [{article_id}] {title}\n   엔티티: {entity_str}"
    else:
        error = result.get("error", "Unknown error")
        url = result.get("source_url", "?")
        return f"❌ {url}\n   에러: {error}"


# === Standalone Telegram bot mode ===

def run_telegram_bot():
    """
    독립 Telegram bot으로 실행합니다.
    URL이 포함된 메시지를 받으면 자동으로 ingest합니다.
    """
    try:
        from telegram import Update
        from telegram.ext import Application, MessageHandler, filters
    except ImportError:
        logger.error(
            "python-telegram-bot not installed. "
            "Install: pip install python-telegram-bot"
        )
        sys.exit(1)

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable required")
        sys.exit(1)

    async def handle_message(update: Update, context):
        """URL이 포함된 메시지 처리."""
        if not update.message or not update.message.text:
            return

        text = update.message.text
        results = process_message(text)

        if results:
            response = "\n\n".join(format_result(r) for r in results)
            await update.message.reply_text(
                f"📚 Knowledge Base 업데이트:\n\n{response}"
            )

    app = Application.builder().token(token).build()
    # URL이 포함된 모든 메시지에 반응
    app.add_handler(MessageHandler(
        filters.TEXT & filters.Entity("url"),
        handle_message,
    ))

    logger.info("Telegram ingest bot started (auto-post mode)")
    app.run_polling()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 테스트 모드: 인자로 받은 텍스트에서 URL 추출 및 ingest
        test_text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Check https://example.com"
        print(f"Extracting URLs from: {test_text}")
        urls = extract_urls(test_text)
        print(f"Found URLs: {urls}")
        for url in urls:
            print(f"\nIngesting: {url}")
            result = ingest_url(url)
            print(format_result(result))
    else:
        run_telegram_bot()
