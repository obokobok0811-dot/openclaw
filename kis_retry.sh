#!/usr/bin/env bash
set -euo pipefail
mkdir -p /Users/andy/.openclaw/workspace/outputs
REAL_URL="https://openapi.koreainvestment.com:9443"
REAL_APP_KEY="REDACTED"
REAL_APP_SECRET="REDACTED+8VPPNlm491JU40b/vZSqaqNdJTbxh0N/REDACTED+REDACTED/jJZV/iP/REDACTED="
attempt_files=()
success=false
token_file=""
for i in 1 2 3; do
  echo "Attempt $i: POST to /oauth2/tokenP"
  out="/Users/andy/.openclaw/workspace/outputs/REDACTED${i}.json"
  curl -s -X POST "$REAL_URL/oauth2/tokenP" -u "$REAL_APP_KEY:$REAL_APP_SECRET" -H "Content-Type: application/REDACTED" --data "grant_type=client_credentials" -o "$out" || true
  attempt_files+=("$out")
  if grep -q "access_token" "$out" 2>/dev/null; then
    success=true
    token_file="$out"
    break
  fi
  echo "Attempt $i: POST to /oauth2/token (fallback)"
  out2="/Users/andy/.openclaw/workspace/outputs/REDACTED${i}_fallback.json"
  curl -s -X POST "$REAL_URL/oauth2/token" -u "$REAL_APP_KEY:$REAL_APP_SECRET" -H "Content-Type: application/REDACTED" --data "grant_type=client_credentials" -o "$out2" || true
  attempt_files+=("$out2")
  if grep -q "access_token" "$out2" 2>/dev/null; then
    success=true
    token_file="$out2"
    break
  fi
  sleep 10
done
summary="/Users/andy/.openclaw/workspace/outputs/REDACTED.json"
printf '{"attempts":[' > "$summary"
first=true
for f in "${attempt_files[@]}"; do
  if [ "$first" = true ]; then first=false; else printf ',' >> "$summary"; fi
  # embed raw content as JSON string
  content=$(python3 -c 'import json,sys; print(json.dumps(open(sys.argv[1]).read()))' "$f")
  printf '%s' "$content" >> "$summary"
done
printf '],"success":%s' "${success}" >> "$summary"
if [ "$success" = true ]; then
  printf ',"token_file":"%s"' "$token_file" >> "$summary"
else
  # copy last attempt file to final error
  last="${attempt_files[-1]}"
  cp "$last" /Users/andy/.openclaw/workspace/outputs/REDACTED.json 2>/dev/null || true
fi
printf '}' >> "$summary"
echo Done
