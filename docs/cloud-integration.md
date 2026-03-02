# Cloud Integration (PAUSED — Offline-First)

**Status:** Cloud integration is temporarily disabled. The system runs fully offline-first.  
This document is retained as a historical reference for future re-enable work.

## Scope (Historical Reference)
- Cloud provider: OpenAI
- Connectivity states: `ONLINE`, `OFFLINE` only
- Rewriter: always local (`llama3.2:3b`)
- Emergency workflow: always local-only (cloud-independent)
- No RELAY-specific logic in this feature

## Control Model
- Master switch: `RESKIOSK_CLOUD_ENABLED`
- Operator toggle: Console -> `Network Setup` -> "Enable Cloud Language Services"
- Toggle persistence is stored in `network_config`:
  - `cloud_enabled`
  - `cloud_user_overridden`
  - `cloud_last_changed_at`

### Toggle rules
- If admin attempts to enable cloud while hub is OFFLINE, API returns `409` with message:
  - `No internet connection detected.`
- Auto-enable behavior only applies when:
  - internet is `ONLINE`
  - `cloud_user_overridden == 0`
  - `RESKIOSK_CLOUD_ENABLED=true`
- Manual OFF is sticky (`cloud_user_overridden=1`) until admin changes it.

## Connectivity Endpoint
- `GET /system/connectivity`
- Returns:
  - `status` (`ONLINE|OFFLINE`)
  - `latency_ms`
  - `checked_at`
  - `cloud_available`
  - `cloud_enabled`
  - `reason`

## Formatter Routing
Formatter contract is shared between local and cloud formatters:
- Contract file: `hub/retrieval/formatter_contract.py`
- Local path: `hub/retrieval/formatter.py`
- Cloud path: `hub/services/cloud_formatter.py`

Cloud formatter is attempted only when:
- hub status is `ONLINE`
- `cloud_available=true`
- operator toggle `cloud_enabled=true`

Fallback:
- one cloud attempt only
- on timeout/error/quota: immediate local formatter fallback in same request

## STT/TTS Cloud Proxy Endpoints
To keep API keys hub-only, cloud language services are proxied by hub.

### STT Proxy
- `POST /cloud/stt/transcribe`
- multipart upload with audio + metadata
- success returns:
  - `transcript`
  - `detected_language`
  - `detection_confidence`
  - `engine_mode=cloud`
- failure returns structured fallback signal:
  - `engine_mode=local_fallback`
  - `fallback_reason`

### TTS Proxy
- `POST /cloud/tts/synthesize`
- JSON input:
  - `text`
  - `language`
  - `voice` (optional)
- success returns audio with header:
  - `X-TTS-Mode: cloud`
- failure returns 503 with header:
  - `X-TTS-Mode: local_fallback`

## Privacy Enforcement
Cloud audio handling is memory-only:
- audio bytes are not written to disk
- raw audio is not logged
- fallback/error paths keep the same no-persistence behavior

## Logging Fields
`query_logs` now includes:
- `formatter_mode` (`cloud|local`)
- `stt_mode` (kiosk-reported)
- `tts_mode` (kiosk-reported)
- `connectivity_state` (`ONLINE|OFFLINE`)
- `cloud_consent_mode` (`operator|session|disabled`)

## Environment Variables
- `RESKIOSK_CLOUD_ENABLED=false`
- `OPENAI_API_KEY=...`
- `RESKIOSK_CONNECTIVITY_ONLINE_MS=1000`
- `RESKIOSK_CLOUD_FORMAT_TIMEOUT_SECS=2.0`
- `RESKIOSK_CLOUD_STT_TIMEOUT_SECS=3.0`
- `RESKIOSK_CLOUD_TTS_TIMEOUT_SECS=3.0`
- `RESKIOSK_CLOUD_STT_CONFIDENCE_THRESHOLD=0.85`
- `RESKIOSK_CLOUD_CONSENT_MODE=operator|session`
- `RESKIOSK_CLOUD_OPERATOR_ENABLED=false`
- `RESKIOSK_CLOUD_CONSENT_DEFAULT` (deprecated alias, still read)
- `RESKIOSK_CLOUD_FORMATTER_DAILY_CAP`
- `RESKIOSK_CLOUD_STT_DAILY_CAP`
- `RESKIOSK_CLOUD_TTS_DAILY_CAP`

## Startup Behavior
If cloud is enabled but `OPENAI_API_KEY` is missing, hub remains operational in local-only mode and marks cloud unavailable in connectivity responses.
