"""
Humanizer: strips AI writing patterns from text.

Based on Wikipedia's 'Signs of AI writing' and observed LLM output patterns.
Designed for Claude Opus 4.6 but applicable to any LLM output.

Usage:
    from skills.humanizer.humanizer import humanize
    clean = humanize(text)
"""

import json
import re
import os
from pathlib import Path

PATTERNS_PATH = Path(__file__).parent / "patterns.json"

_patterns_cache = None


def _load_patterns():
    global _patterns_cache
    if _patterns_cache is None:
        with open(PATTERNS_PATH) as f:
            _patterns_cache = json.load(f)
    return _patterns_cache


def _apply_stock_replacements(text: str, category: dict) -> str:
    """Apply simple phrase replacements from a category.
    Sorts by length descending so 'streamlines' matches before 'streamline'.
    """
    replacements = category.get("replacements", {})
    # Sort longest-first to prevent partial matches
    sorted_phrases = sorted(replacements.keys(), key=len, reverse=True)
    for phrase in sorted_phrases:
        replacement = replacements[phrase]
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        text = pattern.sub(replacement, text)
    return text


def _clean_double_spaces(text: str) -> str:
    """Collapse multiple spaces and fix punctuation artifacts."""
    # Multiple spaces to single
    text = re.sub(r"  +", " ", text)
    # Space before punctuation
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)
    # Double punctuation from removals
    text = re.sub(r"([.,;:])(\s*[.,;:])+", r"\1", text)
    # Capitalize after period if removal left lowercase
    text = re.sub(r"\.\s+([a-z])", lambda m: ". " + m.group(1).upper(), text)
    # Leading space on lines
    text = re.sub(r"^\s+", "", text, flags=re.MULTILINE)
    # Empty lines collapse (max 2 consecutive newlines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _fix_em_dashes(text: str) -> str:
    """Replace em/en dashes with commas. AI overuses these."""
    # Em dash or en dash with surrounding spaces
    text = re.sub(r"\s*[—–]\s*", ", ", text)
    # Fix double commas that might result
    text = re.sub(r",\s*,", ",", text)
    return text


def _remove_participle_tails(text: str) -> str:
    """Remove trailing participial phrases that add superficial analysis.

    Wikipedia identifies this as a key AI tell: sentences ending with
    ', highlighting/underscoring/emphasizing...' that state the obvious.
    """
    participles = (
        "highlighting", "underscoring", "emphasizing", "ensuring",
        "reflecting", "symbolizing", "contributing to", "cultivating",
        "fostering", "showcasing", "demonstrating", "illustrating",
        "signaling", "reinforcing", "solidifying", "cementing",
        "encapsulating", "epitomizing", "embodying", "championing",
        "spearheading", "marking", "representing", "paving",
        "setting the stage", "underscoring",
    )
    participle_pattern = "|".join(re.escape(p) for p in participles)
    # Match ', <participle> ... <end of sentence or end of string>'
    pattern = rf",\s+(?:{participle_pattern})\s+[^.!?\n]*[.!?]?"
    text = re.compile(pattern, re.IGNORECASE).sub(".", text)
    # Also handle at end of string without punctuation
    pattern2 = rf",\s+(?:{participle_pattern})\s+[^.!?\n]*$"
    text = re.compile(pattern2, re.IGNORECASE | re.MULTILINE).sub(".", text)
    # Clean up double periods
    text = text.replace("..", ".").replace(". .", ".")
    return text


def _strip_emoji_from_headers(text: str) -> str:
    """Remove emoji decorations from markdown headers."""
    # Match any emoji character (broad range)
    text = re.sub(
        r"^(#{1,6}\s*)((?:[\U0001F000-\U0001FFFF]|[\U00002600-\U000027BF]|[\U0000FE00-\U0000FE0F]|\U0000200D)+\s*)+",
        r"\1",
        text,
        flags=re.MULTILINE,
    )
    return text
    return text


def _deflate_significance(text: str) -> str:
    """Tone down significance inflation words in context.

    Rather than blanket-replacing (which can break meaning), this handles
    the most common AI inflation patterns where the word adds nothing.
    """
    # "plays a [vital/crucial/pivotal/significant/key] role" -> "matters"
    text = re.sub(
        r"plays\s+a\s+(vital|crucial|pivotal|significant|key|important|critical)\s+role",
        "matters",
        text,
        flags=re.IGNORECASE,
    )
    # "a [vital/crucial/pivotal] [moment/step/part]" -> "a [moment/step/part]"
    text = re.sub(
        r"\ba\s+(vital|crucial|pivotal|critical|monumental)\s+(moment|step|part|component|element|aspect|factor)",
        r"a \2",
        text,
        flags=re.IGNORECASE,
    )
    # "[truly/really/incredibly/remarkably] [adjective]" -> "[adjective]"
    text = re.sub(
        r"\b(truly|really|incredibly|remarkably|exceptionally|extraordinarily)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _fix_sentence_openers(text: str) -> str:
    """Flag and vary repetitive sentence openers.

    AI often starts 3+ consecutive sentences with the same word.
    This doesn't auto-fix (too risky) but collapses the most egregious
    pattern: consecutive 'This' or 'The' openers.
    """
    # Split into sentences (rough)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) < 3:
        return text

    # Detect runs of same opener
    i = 0
    while i < len(sentences) - 2:
        opener = sentences[i].split()[0].lower() if sentences[i].split() else ""
        if opener in ("this", "the", "it", "these", "there"):
            run = 1
            for j in range(i + 1, len(sentences)):
                next_opener = sentences[j].split()[0].lower() if sentences[j].split() else ""
                if next_opener == opener:
                    run += 1
                else:
                    break
            # If 3+ consecutive, we just note it (could add variation logic later)
            # For now, we don't auto-rewrite sentence structure
            i += run
        else:
            i += 1

    return text


def _remove_throat_clearing(text: str) -> str:
    """Remove opening throat-clearing sentences that add no content.

    AI often starts with a meta-sentence about what it's about to do:
    'Let me explain...', 'Here's a breakdown...', 'I'll walk you through...'
    """
    throat_clearers = [
        r"^(?:Let me|Allow me to|I'll|I will)\s+(?:explain|break down|walk you through|outline|summarize|provide|give you|share)\b[^.!?\n]*[.!?]\s*",
        r"^(?:Here's a|Here is a)\s+(?:breakdown|summary|overview|look|rundown|guide)\b[^.!?\n]*[.!?]\s*",
        r"^(?:In this|In the following)\s+(?:section|article|guide|document|post|piece)[^.!?\n]*[.!?]\s*",
        r"^(?:Before we begin|Before diving in|Before we get started)[^.!?\n]*[.!?]\s*",
    ]
    for pattern in throat_clearers:
        text = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE)
    return text


def humanize(text: str, aggressive: bool = False) -> str:
    """Strip AI writing patterns from text.

    Args:
        text: The text to humanize.
        aggressive: If True, also removes significance inflation words
                    and sentence opener repetition fixes. Default False
                    keeps a lighter touch.

    Returns:
        Cleaned text with AI patterns removed.
    """
    if not text or len(text.strip()) < 50:
        return text

    patterns = _load_patterns()

    # Phase 1: Remove throat-clearing openers
    text = _remove_throat_clearing(text)

    # Phase 2: Stock phrase replacements
    for category_name in ("stock_phrases", "performed_authenticity", "hedging"):
        category = patterns["categories"].get(category_name, {})
        text = _apply_stock_replacements(text, category)

    # Phase 3: Structural patterns
    text = _fix_em_dashes(text)
    text = _remove_participle_tails(text)
    text = _strip_emoji_from_headers(text)

    # Phase 4: Significance deflation (always applied, light touch)
    text = _deflate_significance(text)

    # Phase 5: Aggressive mode extras
    if aggressive:
        text = _fix_sentence_openers(text)

    # Phase 6: Clean up artifacts
    text = _clean_double_spaces(text)

    return text


def should_humanize(text: str) -> bool:
    """Decide whether text should be run through the humanizer.

    Returns True for user-facing prose longer than ~3 sentences.
    Returns False for code, JSON, short replies, or structured data.
    """
    if not text:
        return False

    stripped = text.strip()

    # Too short
    if len(stripped) < 200:
        return False

    # Mostly code or structured data
    code_indicators = stripped.count("```") + stripped.count("    ") + stripped.count("{")
    prose_chars = len(re.sub(r"```.*?```", "", stripped, flags=re.DOTALL))
    if prose_chars < 150:
        return False

    # JSON or code-heavy
    if stripped.startswith("{") or stripped.startswith("[") or stripped.startswith("```"):
        return False

    return True


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        with open(input_file) as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    print(humanize(text))
