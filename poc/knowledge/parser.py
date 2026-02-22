#!/usr/bin/env python3
"""
parser.py - 텍스트 파싱/정제 모듈

HTML → clean text 변환, 불필요한 태그 제거, 본문 추출
collector.py의 결과를 추가 정제할 때 사용
"""

import re
import logging

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logger.warning("BeautifulSoup not installed. Install: pip install beautifulsoup4")


# 제거할 HTML 태그들
STRIP_TAGS = [
    "script", "style", "nav", "footer", "header", "aside",
    "iframe", "noscript", "form", "button", "input",
    "meta", "link", "svg", "canvas",
]

# 광고/네비게이션 관련 class/id 패턴
NOISE_PATTERNS = re.compile(
    r"(sidebar|comment|footer|header|nav|menu|ad[s]?|banner|widget|popup|modal|cookie|consent)",
    re.IGNORECASE,
)

# 최소 의미있는 텍스트 길이
MIN_PARAGRAPH_LENGTH = 20


def parse_html(html: str) -> str:
    """
    HTML을 정제된 plain text로 변환합니다.

    Args:
        html: raw HTML 문자열

    Returns:
        정제된 plain text
    """
    if BeautifulSoup is not None:
        return _parse_with_bs4(html)
    return _parse_basic(html)


def _parse_with_bs4(html: str) -> str:
    """BeautifulSoup을 사용한 HTML 파싱."""
    soup = BeautifulSoup(html, "html.parser")

    # 불필요한 태그 제거
    for tag_name in STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # 노이즈 패턴 매칭되는 요소 제거
    for element in soup.find_all(True):
        classes = " ".join(element.get("class", []))
        elem_id = element.get("id", "")
        if NOISE_PATTERNS.search(classes) or NOISE_PATTERNS.search(elem_id):
            element.decompose()

    # 텍스트 추출
    text = soup.get_text(separator="\n", strip=True)
    return clean_text(text)


def _parse_basic(html: str) -> str:
    """정규식 기반 기본 HTML 파싱."""
    text = html
    # script, style 제거
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # 모든 태그 제거
    text = re.sub(r"<[^>]+>", "\n", text)
    # HTML entities
    text = _decode_entities(text)
    return clean_text(text)


def clean_text(text: str) -> str:
    """
    텍스트를 정제합니다.

    - 연속 공백/빈줄 정리
    - 짧은 줄(노이즈) 필터링
    - 앞뒤 공백 제거

    Args:
        text: 정제할 텍스트

    Returns:
        정제된 텍스트
    """
    lines = text.split("\n")

    cleaned = []
    for line in lines:
        line = line.strip()
        # 빈 줄은 단락 구분으로 유지 (연속 빈줄은 하나로)
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        # 매우 짧고 의미 없는 줄 필터링 (숫자만, 특수문자만 등)
        if len(line) < 5 and not re.search(r"[가-힣a-zA-Z]", line):
            continue
        cleaned.append(line)

    result = "\n".join(cleaned).strip()

    # 연속 빈줄 정리
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result


def extract_paragraphs(text: str, min_length: int = MIN_PARAGRAPH_LENGTH) -> list[str]:
    """
    텍스트에서 의미 있는 단락만 추출합니다.

    Args:
        text: 입력 텍스트
        min_length: 최소 단락 길이

    Returns:
        의미 있는 단락 리스트
    """
    paragraphs = re.split(r"\n\s*\n", text)
    return [p.strip() for p in paragraphs if len(p.strip()) >= min_length]


def _decode_entities(text: str) -> str:
    """HTML entities를 디코딩합니다."""
    import html
    try:
        return html.unescape(text)
    except Exception:
        # 기본 entities만 수동 변환
        replacements = {
            "&amp;": "&", "&lt;": "<", "&gt;": ">",
            "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
        }
        for entity, char in replacements.items():
            text = text.replace(entity, char)
        return text


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python parser.py <html_file>")
        print("  or pipe HTML: echo '<html>...</html>' | python parser.py -")
        sys.exit(1)

    if sys.argv[1] == "-":
        html_input = sys.stdin.read()
    else:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            html_input = f.read()

    result = parse_html(html_input)
    print(result)
