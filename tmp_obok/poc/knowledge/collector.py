#!/usr/bin/env python3
"""
collector.py - URL에서 콘텐츠를 수집하는 모듈

입력: URL
출력: dict with title, content (raw HTML), cleaned_text
"""

import logging

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    requests = None
    logger.warning("requests not installed. Install: pip install requests")

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logger.warning("BeautifulSoup not installed. Install: pip install beautifulsoup4")

try:
    from readability import Document as ReadabilityDocument
except ImportError:
    ReadabilityDocument = None
    logger.debug("readability-lxml not installed (optional). Install: pip install readability-lxml")


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def collect(url: str, timeout: int = 15) -> dict:
    """
    URL에서 콘텐츠를 수집합니다.

    Args:
        url: 수집할 URL
        timeout: 요청 타임아웃 (초)

    Returns:
        dict: {
            "url": str,
            "title": str,
            "content": str (raw HTML),
            "cleaned_text": str (plain text)
        }

    Raises:
        RuntimeError: requests가 설치되지 않은 경우
        requests.RequestException: HTTP 요청 실패 시
    """
    if requests is None:
        raise RuntimeError("requests library is required. pip install requests")

    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    html = resp.text

    title = ""
    cleaned_text = ""

    # readability-lxml이 있으면 우선 사용 (가장 정확한 본문 추출)
    if ReadabilityDocument is not None:
        try:
            doc = ReadabilityDocument(html)
            title = doc.title() or ""
            article_html = doc.summary()
            if BeautifulSoup is not None:
                soup = BeautifulSoup(article_html, "html.parser")
                cleaned_text = soup.get_text(separator="\n", strip=True)
            else:
                cleaned_text = _strip_tags_basic(article_html)
        except Exception as e:
            logger.warning(f"readability failed, falling back to BeautifulSoup: {e}")

    # fallback to BeautifulSoup
    if not cleaned_text and BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        title = title or (soup.title.string if soup.title else "")

        # 불필요한 태그 제거
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "iframe", "noscript"]):
            tag.decompose()

        # 본문 추출 시도
        article = soup.find("article") or soup.find("main") or soup.find("body")
        if article:
            cleaned_text = article.get_text(separator="\n", strip=True)
        else:
            cleaned_text = soup.get_text(separator="\n", strip=True)

    # 최종 fallback: 기본 태그 제거
    if not cleaned_text:
        cleaned_text = _strip_tags_basic(html)
        # title 추출 시도
        import re
        m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if m:
            title = m.group(1).strip()

    # 빈 줄 정리
    lines = [line.strip() for line in cleaned_text.split("\n")]
    cleaned_text = "\n".join(line for line in lines if line)

    return {
        "url": url,
        "title": title.strip() if title else "",
        "content": html,
        "cleaned_text": cleaned_text,
    }


def _strip_tags_basic(html: str) -> str:
    """기본적인 태그 제거 (라이브러리 없이)."""
    import re
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python collector.py <url>")
        sys.exit(1)

    result = collect(sys.argv[1])
    # content는 너무 길어서 출력에서 제외
    output = {k: (v[:200] + "..." if k == "content" and len(v) > 200 else v)
              for k, v in result.items()}
    print(json.dumps(output, ensure_ascii=False, indent=2))
