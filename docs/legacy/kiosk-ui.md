# Kiosk UI - Current Implementation

**Note:** Cloud integration is currently disabled. Kiosk behavior is fully offline-first.

This document describes the current Android kiosk UI behavior after the recent overhaul.

## Scope

Primary files:
- `kiosk/app/src/main/java/com/reskiosk/ui/MainKioskScreen.kt`
- `kiosk/app/src/main/java/com/reskiosk/viewmodel/KioskViewModel.kt`
- `kiosk/app/src/main/java/com/reskiosk/emergency/EmergencyStrings.kt`
- `kiosk/app/src/main/res/drawable-nodpi/reskiosk_2d_logo.png`

## Start Session Experience

The kiosk shows a centered start screen (`StartSessionHero`) when no session is active.

Behavior:
- Centered logo (`reskiosk_2d_logo`).
- Localized title/subtitle from `EmergencyStrings`:
  - `start_title`
  - `start_subtitle_line_1`
  - `start_subtitle_line_2`
  - `start_button`
- Subtitle is rendered as two explicit one-line rows.
- Hero container is offset slightly upward (`~10dp`) for better visual balance.
- Starts a session only if hub URL is configured.
- If hub is not configured, user gets a connection prompt dialog.

## Session Defaults and Lifecycle

When `startSession()` runs:
- Chat mode resets to `VOICE_ONLY`.
- Chat history is cleared.
- Loading overlay is cleared.
- Emergency state and cooldown state are reset.
- Inactivity timer is started.

When `endSession()` runs:
- Active emergency alert is dismissed to hub if present.
- Session state and chat history are cleared.
- Chat mode resets to `VOICE_ONLY`.
- Session-ending TTS is spoken once:
  - `session_ending` string key.

## Chat Modes

Chat mode enum:
- `VOICE_ONLY`
- `TEXT_VOICE`

Mode toggle:
- Rendered in the top header during active sessions.
- Disabled while loading/transcribing/processing/listening.

`VOICE_ONLY` mode behavior:
- User messages are hidden from the chat feed.
- Live listening transcript bubble is hidden.
- Only assistant messages are shown.
- Tap-to-speak button is larger.
- While listening, a dark overlay appears and orange waveform bars render behind the button.

`TEXT_VOICE` mode behavior:
- User and assistant messages are shown.
- A wide `Keyboard` button toggles a text composer.
- Text composer uses an inline input + send button.
- Sending typed text calls `submitTypedQuery()` and follows the same query pipeline as voice (including emergency detection).

## Query Loading Overlay

The old in-chat "Asking hub..." placeholder is replaced by a full-screen blocker overlay during:
- `KioskState.Transcribing`
- `KioskState.Processing`

Overlay content:
- Spinner.
- Randomized localized title (5 variants):
  - `asking_hub_title_1` to `asking_hub_title_5`
- Localized subtitle:
  - `asking_hub_subtitle`

Selection logic:
- Title is randomized once at request start (`beginLoadingOverlay()`).
- Overlay is cleared when query completes or errors (`clearLoadingOverlay()`).

## Voice Interaction Behavior

Tap-to-speak flow:
- Tap once -> `PreparingToListen` brief delay.
- Then -> `Listening`.
- Tap again -> recording stops, transcribing starts.

Important audio handling:
- TTS is stopped before recording to reduce TTS-to-mic bleed.
- Pre-buffer is cleared before capture.
- A short delay is applied before starting capture.
- Voice waveform levels come from RMS-based smoothing in `updateVoiceLevels()`.

Emergency detection guard:
- Generic informational "help" is not treated as SOS by itself.
- Informational queries like "where is the doctor?" stay in Q&A unless critical emergency phrases/keywords are present.

## Header Controls

During active session, top-right controls are shown:
- SOS button (same size style as end-session button).
- End Session (close icon).

SOS behavior:
- Disabled during emergency cooldown.
- Opens a hold-to-confirm dialog.

## SOS Hold-to-Confirm

Dialog component: `SosHoldToConfirmDialog`.

Behavior:
- Shows localized warning text and instruction.
- Requires press-and-hold for 3 seconds.
- Progress bar fills while holding.
- Releasing early cancels trigger.
- Completing hold calls `onSosButtonPressed()`.

String keys:
- `sos_confirm_title`
- `sos_confirm_body`
- `sos_hold_instruction`
- `sos_hold_button`
- `cancel_button`

## Dashboard Emergency Mode Broadcast

Kiosk also listens for dashboard-wide emergency mode activation via `GET /admin/ping` (5-second poll).

Behavior when `emergency_mode_active=true` with a new `emergency_mode_activated_at`:
- Show full-screen emergency overlay for 5 seconds.
- Play local bundled alarm once (`res/raw/emergencycallalert.mp3`).
- After overlay timeout, keep animated top and bottom emergency banners visible.

Behavior when deactivated:
- Overlay and banners are removed immediately.

Replay protection:
- Last seen activation timestamp is stored in prefs (`last_seen_emergency_mode_activated_at`) to avoid replaying the alarm on every poll.

## Hub URL Reliability Rules

Hub URL is normalized before save/probe:
- Trims whitespace.
- Adds `http://` when scheme is missing.
- Defaults port to `8000` if omitted.
- Rejects invalid host strings.

Reachability probing:
- Tries `GET /admin/ping` first.
- Falls back to `GET /health`.
- If `ping` fails but `health` succeeds, kiosk also sends `POST /register_kiosk` heartbeat to keep hub-side kiosk presence accurate.

## Compound Follow-Up Auto-Answer

When the hub returns a primary answer with `follow_up_prompt` + `follow_up_intent`:

- Kiosk stores the follow-up context for exactly one next turn.
- If next user message is an agreement phrase (EN/ES/DE/FR/JA plus shelter variants like `opo`, `sige`, `oo`), kiosk automatically triggers retrieval for the secondary intent.
- If next message is not agreement, context is cleared and query runs normally.
- Follow-up context always expires after one turn.

## Emergency UI Screens

Main emergency states rendered from `MainPage`:
- `EmergencyConfirmation`
- `EmergencyCancelWindow`
- `EmergencyPending`
- `EmergencyActive`
- `EmergencyAcknowledged`
- `EmergencyResponding`
- `EmergencyResolved`
- `EmergencyFailed`
- `EmergencyCancelled`

Current design uses `EmergencyStatePanel` for most steady states with per-state colors and messaging.

## Localization

Centralized in `EmergencyStrings.kt`.

Languages available:
- `en`
- `es`
- `de`
- `fr`
- `ja`

New kiosk-specific keys include:
- Start screen keys (`start_*`)
- Mode toggle keys (`mode_*`)
- Text input keys (`keyboard_open`, `input_placeholder`, `send`)
- Voice/text hints (`voice_only_hint`, `text_voice_hint`)
- Loading overlay keys (`asking_hub_title_*`, `asking_hub_subtitle`)
- SOS hold-confirm keys (`sos_confirm_*`, `sos_hold_*`, `cancel_button`)

## Notes for Future Changes

- This implementation keeps mode state session-scoped (not persisted between sessions).
 - Voice-only mode intentionally hides user bubbles but still records full internal query metadata for retry/feedback.
 - Emergency flow details and hub/console lifecycle are documented separately in `docs/emergency-calls.md`.
