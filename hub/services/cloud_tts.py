import os

import requests

from hub.services.cloud_quota import reserve


class CloudTTSError(Exception):
    pass


def synthesize_speech(text: str, language: str, voice: str | None = None) -> tuple[bytes, str]:
    api_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not api_key:
        raise CloudTTSError("OPENAI_API_KEY missing")

    allowed, reason = reserve("tts")
    if not allowed:
        raise CloudTTSError(reason or "tts daily cap reached")

    timeout_secs = float(os.environ.get("RESKIOSK_CLOUD_TTS_TIMEOUT_SECS", "3.0"))
    endpoint = os.environ.get("RESKIOSK_OPENAI_TTS_URL", "https://api.openai.com/v1/audio/speech")
    payload = {
        "model": os.environ.get("RESKIOSK_CLOUD_TTS_MODEL", "tts-1"),
        "voice": voice or os.environ.get("RESKIOSK_CLOUD_TTS_VOICE", "nova"),
        "input": text,
        "format": "mp3",
        "language": language,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=timeout_secs,
        )
        response.raise_for_status()
        return response.content, "audio/mpeg"
    except Exception as exc:
        raise CloudTTSError(str(exc)) from exc

