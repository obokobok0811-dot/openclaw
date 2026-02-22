#!/bin/bash
DN="memory/$(date +%F).md"
mkdir -p memory
if [ ! -f "$DN" ]; then
  cat > "$DN" <<EOF
# Daily Notes — $(date '+%Y-%m-%d')
시간대: Asia/Seoul

## Timeline
- 

## Inbound messages (summary)
- 

## Decisions (#decision)
- 

## Todos (#todo)
- 

EOF
  echo "created $DN"
else
  echo "$DN already exists"
fi
