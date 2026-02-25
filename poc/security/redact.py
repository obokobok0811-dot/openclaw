#!/usr/bin/env python3
"""Outbound message redaction filter.
Usage: import and call redact(text) before sending any message."""
import re

PATTERNS = [
    ('AWS Key', re.compile(r'AKIA[0-9A-Z]{16}')),
    ('Google API Key', re.compile(r'AIza[0-9A-Za-z_-]{35}')),
    ('OpenAI Key', re.compile(r'sk-[A-Za-z0-9]{32,}')),
    ('Slack Token', re.compile(r'xox[bpas]-[A-Za-z0-9-]{10,}')),
    ('Telegram Bot Token', re.compile(r'\d{8,10}:AA[A-Za-z0-9_-]{33,}')),
    ('OAuth Secret', re.compile(r'GOCSPX-[A-Za-z0-9_-]{20,}')),
    ('Client Secret', re.compile(r'client_secret["\']\s*:\s*["\'][A-Za-z0-9_-]{10,}')),
    ('Private Key', re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')),
    ('JWT', re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')),
    ('Generic Token', re.compile(r'(?:password|secret|token|api_key)\s*[=:]\s*["\'][A-Za-z0-9_/+=-]{8,}["\']')),

    ('Email Address', re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')),
    ('Phone Number KR', re.compile(r'01[0-9]-?\d{3,4}-?\d{4}')),
    ('Phone Number Intl', re.compile(r'\+\d{1,3}[- ]?\d{2,4}[- ]?\d{3,4}[- ]?\d{3,4}')),
    ('Dollar Amount', re.compile(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?')),
    ('Won Amount', re.compile(r'\d{1,3}(?:,\d{3})*\s*[원]')),
    ('Bearer Token', re.compile(r'Bearer\s+[A-Za-z0-9_\-\.]{20,}')),
    ('ElevenLabs Key', re.compile(r'sk_[a-f0-9]{40,}')),
    ('Brave API Key', re.compile(r'BSA[A-Za-z0-9_]{20,}')),
]

def redact(text):
    """Redact credentials from text. Returns (redacted_text, list_of_redactions)."""
    redactions = []
    result = text
    for name, pat in PATTERNS:
        for m in pat.finditer(result):
            redactions.append({'type': name, 'position': m.start(), 'preview': m.group(0)[:8] + '...'})
            result = result[:m.start()] + '[REDACTED]' + result[m.end():]
    return result, redactions

def is_financial(text):
    """Check if text contains financial data patterns."""
    financial_keywords = ['revenue', 'profit', 'salary', 'billing', 'invoice',
                         '매출', '수익', '급여', '청구', '결제', '비용', '계약금',
                         'deal amount', 'ARR', 'MRR', 'cost', 'budget']
    lower = text.lower()
    return any(kw.lower() in lower for kw in financial_keywords)

if __name__ == '__main__':
    # Test
    test = 'My token is 1234567890:AAabcdefghijklmnopqrstuvwxyz123456 and key is AIzaSyB-example1234567890123456789012'
    redacted, found = redact(test)
    print(f'Original: {test}')
    print(f'Redacted: {redacted}')
    print(f'Found: {found}')
