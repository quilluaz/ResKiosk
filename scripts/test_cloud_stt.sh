#!/usr/bin/env bash
set -euo pipefail

HUB_URL="${1:-http://localhost:8000}"
AUDIO_PATH="${2:-}"

if [[ -z "${AUDIO_PATH}" || ! -f "${AUDIO_PATH}" ]]; then
  echo "Usage: ./scripts/test_cloud_stt.sh <hub_url> <audio.wav>"
  exit 1
fi

curl -sS -X POST "${HUB_URL}/cloud/stt/transcribe" \
  -F "session_id=test-session" \
  -F "kiosk_id=test-kiosk" \
  -F "hint_language=en" \
  -F "auto_detect=true" \
  -F "audio=@${AUDIO_PATH}" | jq .

