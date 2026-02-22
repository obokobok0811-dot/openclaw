#!/usr/bin/env python3
"""
ner.py - 경량 Named Entity Recognition (정규식 기반)

spaCy 없이 정규식으로 한국어/영어 엔티티를 추출합니다.
추출 대상: 인물(persons), 회사/조직(orgs), 날짜(dates), 금액(amounts)
"""

import re
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# === 인물 패턴 ===

# 한국어 이름: 2~4글자 한글 + 직함
KOREAN_PERSON_SUFFIXES = r"(?:대표|사장|회장|이사|교수|박사|연구원|위원장?|장관|의원|기자|작가|감독|선수|씨|님)"
KOREAN_NAME_PATTERN = re.compile(
    rf"([가-힣]{{2,4}})\s*{KOREAN_PERSON_SUFFIXES}",
    re.UNICODE,
)

# 영어 이름: Title Case 2~3단어 (Mr./Dr. 등 포함)
ENGLISH_NAME_PATTERN = re.compile(
    r"(?:(?:Mr|Mrs|Ms|Dr|Prof|CEO|CTO|CFO)\.?\s+)?"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})"
)

# === 회사/조직 패턴 ===

# 한국어 회사명: ~(주), (주)~, ~주식회사, ~그룹, ~은행 등
KOREAN_ORG_PATTERN = re.compile(
    r"(?:"
    r"(?:주식회사|㈜|\(주\))\s*([가-힣a-zA-Z0-9]+)|"            # (주)회사명
    r"([가-힣a-zA-Z0-9]+)\s*(?:주식회사|㈜|\(주\))|"            # 회사명(주)
    r"([가-힣]{2,10})(?:그룹|은행|증권|보험|전자|바이오|제약|건설|화학|엔터테인먼트|테크)"  # ~그룹 등
    r")",
    re.UNICODE,
)

# 영어 회사명: Inc., Corp., Ltd., LLC, Co. 등
ENGLISH_ORG_PATTERN = re.compile(
    r"([A-Z][A-Za-z0-9&\s]+?)\s*(?:Inc\.?|Corp\.?|Ltd\.?|LLC|Co\.?|Group|Holdings|Technologies|Tech)",
)

# === 날짜 패턴 ===
DATE_PATTERNS = [
    # 2024년 1월 15일, 2024년1월
    re.compile(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일?"),
    re.compile(r"(\d{4})년\s*(\d{1,2})월"),
    # 2024-01-15, 2024/01/15
    re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"),
    # January 15, 2024
    re.compile(
        r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    # 15 Jan 2024
    re.compile(
        r"(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})",
        re.IGNORECASE,
    ),
]

# === 금액 패턴 ===
AMOUNT_PATTERNS = [
    # 한국 원화: 1,000원, 10억원, 1조원, 100만원
    re.compile(r"(\d[\d,]*\.?\d*)\s*(?:조|억|만)?\s*원"),
    # 달러: $1,000, $1.5M, $10B
    re.compile(r"\$\s*(\d[\d,]*\.?\d*)\s*(?:[MBKmb](?:illion|illion)?)?"),
    # USD 1,000
    re.compile(r"(?:USD|EUR|JPY|KRW|GBP)\s*(\d[\d,]*\.?\d*)"),
    # 1,000 달러/유로
    re.compile(r"(\d[\d,]*\.?\d*)\s*(?:달러|유로|엔|파운드|위안)"),
]


def extract_entities(text: str) -> dict:
    """
    텍스트에서 엔티티를 추출합니다.

    Args:
        text: 분석할 텍스트

    Returns:
        dict: {
            "persons": ["이름1", ...],
            "orgs": ["회사1", ...],
            "dates": ["2024-01-15", ...],
            "amounts": ["1000원", ...]
        }
    """
    if not text:
        return {"persons": [], "orgs": [], "dates": [], "amounts": []}

    persons = _extract_persons(text)
    orgs = _extract_orgs(text)
    dates = _extract_dates(text)
    amounts = _extract_amounts(text)

    return {
        "persons": sorted(set(persons)),
        "orgs": sorted(set(orgs)),
        "dates": sorted(set(dates)),
        "amounts": sorted(set(amounts)),
    }


def _extract_persons(text: str) -> list[str]:
    """인물 이름 추출."""
    persons = []

    # 한국어 이름
    for m in KOREAN_NAME_PATTERN.finditer(text):
        name = m.group(1).strip()
        if len(name) >= 2 and not _is_common_korean_word(name):
            persons.append(name)

    # 영어 이름
    for m in ENGLISH_NAME_PATTERN.finditer(text):
        name = m.group(1).strip()
        if not _is_common_english_word(name):
            persons.append(name)

    return persons


def _extract_orgs(text: str) -> list[str]:
    """회사/조직 추출."""
    orgs = []

    # 한국어 조직
    for m in KOREAN_ORG_PATTERN.finditer(text):
        # groups: (주)뒤, (주)앞, ~그룹
        org = m.group(1) or m.group(2) or m.group(3)
        if org:
            full_match = m.group(0).strip()
            orgs.append(full_match)

    # 영어 조직
    for m in ENGLISH_ORG_PATTERN.finditer(text):
        org = m.group(0).strip()
        if len(org) > 3:
            orgs.append(org)

    return orgs


def _extract_dates(text: str) -> list[str]:
    """날짜 추출."""
    dates = []
    for pattern in DATE_PATTERNS:
        for m in pattern.finditer(text):
            dates.append(m.group(0).strip())
    return dates


def _extract_amounts(text: str) -> list[str]:
    """금액 추출."""
    amounts = []
    for pattern in AMOUNT_PATTERNS:
        for m in pattern.finditer(text):
            amounts.append(m.group(0).strip())
    return amounts


# === 필터링 헬퍼 ===

_COMMON_KOREAN_WORDS = frozenset([
    "하지만", "그러나", "그리고", "때문에", "이것은", "그것은",
    "우리는", "그들은", "이러한", "그러한", "또한은", "현재는",
    "최근에", "앞으로", "오늘은", "내일은", "어제는",
])

_COMMON_ENGLISH_WORDS = frozenset([
    "The New", "New York", "United States", "South Korea",
    "North Korea", "In The", "At The", "For The",
    "Read More", "Click Here", "Sign Up", "Log In",
])


def _is_common_korean_word(word: str) -> bool:
    return word in _COMMON_KOREAN_WORDS


def _is_common_english_word(phrase: str) -> bool:
    return phrase in _COMMON_ENGLISH_WORDS


def entities_to_json(entities: dict) -> str:
    """엔티티 dict를 JSON 문자열로 변환."""
    return json.dumps(entities, ensure_ascii=False)


def entities_from_json(json_str: Optional[str]) -> dict:
    """JSON 문자열을 엔티티 dict로 변환."""
    if not json_str:
        return {"persons": [], "orgs": [], "dates": [], "amounts": []}
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return {"persons": [], "orgs": [], "dates": [], "amounts": []}


if __name__ == "__main__":
    # 테스트
    test_text = """
    삼성전자 이재용 회장이 2024년 1월 15일 기자회견을 열고
    반도체 사업에 10조원을 투자하겠다고 발표했다.
    Apple Inc. CEO Tim Cook은 $2.5B 규모의 프로젝트를 발표했다.
    네이버㈜와 카카오그룹도 AI 분야 투자를 확대할 계획이다.
    """
    result = extract_entities(test_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
