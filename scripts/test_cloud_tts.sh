#!/usr/bin/env bash
set -euo pipefail

HUB_URL="${1:-http://localhost:8000}"
OUT_FILE="${2:-cloud_tts_test.mp3}"

curl -sS -X POST "${HUB_URL}/cloud/tts/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a cloud TTS test from ResKiosk.","language":"en","voice":"nova"}' \
  -o "${OUT_FILE}" -D /tmp/reskiosk_cloud_tts_headers.txt

echo "Saved: ${OUT_FILE}"
grep -i "X-TTS-Mode" /tmp/reskiosk_cloud_tts_headers.txt || true

