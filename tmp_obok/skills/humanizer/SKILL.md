# Humanizer Skill

Strips AI writing patterns from text before sending to users.

## When to Use

Run `humanize()` on any user-facing prose longer than ~3 sentences.
Short replies, code, and structured data (JSON, tables) skip humanization.

## How It Works

The humanizer applies pattern-based replacements and structural rewrites
in a single pass. It catches:

1. **Stock phrases** that signal AI authorship
2. **Structural tells** (em dashes, rule of three, participle tails)
3. **Hedging language** that adds no information
4. **Performed authenticity** ("Great question!", "I'm glad you asked")
5. **Significance inflation** ("pivotal", "crucial", "testament to")
6. **Superficial analysis** ("-ing" phrase tails that state the obvious)

## Usage

```python
from skills.humanizer.humanizer import humanize

text = humanize(raw_text)
```

## Files

- `humanizer.py` — main processing module
- `patterns.json` — all pattern definitions (phrases, regex, structural)
- `test_humanizer.py` — regression tests

## Maintenance

When a new AI pattern emerges, add it to `patterns.json` and add a
regression test case in `test_humanizer.py`. Run tests after changes:

```bash
cd skills/humanizer && python -m pytest test_humanizer.py -v
```
