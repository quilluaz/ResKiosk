import os
import threading
import time
from typing import Tuple


_lock = threading.Lock()
_daily_counts: dict[tuple[str, str], int] = {}


def _today_key() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _cap_for(service: str) -> int:
    env_map = {
        "formatter": "RESKIOSK_CLOUD_FORMATTER_DAILY_CAP",
        "stt": "RESKIOSK_CLOUD_STT_DAILY_CAP",
        "tts": "RESKIOSK_CLOUD_TTS_DAILY_CAP",
    }
    raw = os.environ.get(env_map.get(service, ""), "500").strip()
    try:
        return max(0, int(raw))
    except Exception:
        return 500


def reserve(service: str) -> Tuple[bool, str | None]:
    """
    Reserve one cloud call for a service.
    Returns (allowed, reason_if_denied).
    cap <= 0 means unlimited.
    """
    cap = _cap_for(service)
    if cap <= 0:
        return True, None

    key = (service, _today_key())
    with _lock:
        count = _daily_counts.get(key, 0)
        if count >= cap:
            return False, f"{service} daily cloud cap reached"
        _daily_counts[key] = count + 1
    return True, None

