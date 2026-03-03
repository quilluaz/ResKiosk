import os
from typing import Any

import requests

from hub.services.cloud_quota import reserve


class CloudSTTError(Exception):
    pass


def transcribe_audio(
    audio_bytes: bytes,
    hint_language: str | None = None,
    auto_detect: bool = True,
) -> dict[str, Any]:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise CloudSTTError("OPENAI_API_KEY missing")

    allowed, reason = reserve("stt")
    if not allowed:
        raise CloudSTTError(reason or "stt daily cap reached")

    timeout_secs = float(os.environ.get("RESKIOSK_CLOUD_STT_TIMEOUT_SECS", "3.0"))
    endpoint = os.environ.get("RESKIOSK_OPENAI_STT_URL", "https://api.openai.com/v1/audio/transcriptions")

    data = {
        "model": os.environ.get("RESKIOSK_CLOUD_STT_MODEL", "whisper-1"),
        "response_format": "json",
    }
    if hint_language and not auto_detect:
        data["language"] = hint_language

    files = {
        "file": ("audio.wav", audio_bytes, "audio/wav"),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        response = requests.post(
            endpoint,
            data=data,
            files=files,
            headers=headers,
            timeout=timeout_secs,
        )
        response.raise_for_status()
        payload = response.json()
        transcript = (payload.get("text") or "").strip()
        return {
            "transcript": transcript,
            "detected_language": payload.get("language") or hint_language or "unknown",
            "detection_confidence": payload.get("confidence"),
            "engine_mode": "cloud",
            "fallback_reason": None,
        }
    except Exception as exc:
        raise CloudSTTError(str(exc)) from exc
    finally:
        # Explicitly drop references to avoid accidental retention.
        del audio_bytes

