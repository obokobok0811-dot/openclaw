#!/bin/bash
# Simple distillation: append decisions and todos from given daily notes into MEMORY.md
# Usage: ./scripts/distill_daily_to_memory.sh YYYY-MM-DD [YYYY-MM-DD ...]
set -e
mkdir -p memory memory/qmd
OUT="MEMORY.md"
TMP="/tmp/mem_new_$$.md"

echo "# MEMORY (auto-updated)" > "$TMP"
echo "Generated: $(date -u)" >> "$TMP"

echo "" >> "$TMP"
for d in "$@"; do
  FILE="memory/$d.md"
  if [ ! -f "$FILE" ]; then
    echo "Warning: $FILE not found, skipping" >&2
    continue
  fi
  echo "Processing $FILE"
  echo "## From: $d" >> "$TMP"
  # Extract Decisions and Todos
  sed -n '/## Decisions/,/## Todos/p' "$FILE" >> "$TMP" || true
  sed -n '/## Todos/,/##/p' "$FILE" >> "$TMP" || true
  echo "" >> "$TMP"
done

# Append existing MEMORY.md (dedupe naive: append and rely on manual review)
if [ -f "$OUT" ]; then
  echo "" >> "$TMP"
  echo "# Previous MEMORY content" >> "$TMP"
  cat "$OUT" >> "$TMP"
fi

mv "$TMP" "$OUT"
chmod 600 "$OUT" || true

echo "MEMORY.md updated at $OUT"

# Also create a qmd copy for today
QMD="memory/qmd/$(date +%F)_memory.qmd"
cat > "$QMD" <<EOF
---
title: "Memory — $(date +%F)"
date: $(date +%F)
tags: [memory, auto-converted]
source: MEMORY.md
---

Generated from daily notes: $*

$(cat "$OUT")
EOF

chmod 600 "$QMD" || true

echo "QMD created at $QMD"
