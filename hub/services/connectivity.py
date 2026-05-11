import os
import threading
import time
from typing import Any, Dict

import requests


class ConnectivityManager:
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"

    def __init__(self) -> None:
        self._interval_secs = int(os.environ.get("RESKIOSK_CONNECTIVITY_POLL_SECS", "30"))
        self._online_threshold_ms = float(os.environ.get("RESKIOSK_CONNECTIVITY_ONLINE_MS", "1000"))
        self._timeout_secs = float(os.environ.get("RESKIOSK_CONNECTIVITY_TIMEOUT_SECS", "3.0"))
        self._target = os.environ.get("RESKIOSK_CONNECTIVITY_TARGET", "https://api.openai.com")

        self._status = self.OFFLINE
        self._latency_ms = None
        self._checked_at = int(time.time())
        self._reason = "Connectivity probe has not run yet."
        self._started = False
        self._lock = threading.Lock()

    @staticmethod
    def cloud_master_enabled() -> bool:
        return os.environ.get("RESKIOSK_CLOUD_ENABLED", "false").strip().lower() in ("1", "true", "yes", "on")

    @staticmethod
    def has_api_key() -> bool:
        return bool((os.environ.get("OPENAI_API_KEY") or "").strip())

    def _probe_once(self) -> None:
        start = time.time()
        status = self.OFFLINE
        latency_ms = None
        reason = "No internet connection detected."

        try:
            # We only care about reachability/latency, not auth status.
            response = requests.head(self._target, timeout=self._timeout_secs)
            elapsed_ms = (time.time() - start) * 1000.0
            latency_ms = round(elapsed_ms, 1)
            if response.status_code < 500 and elapsed_ms <= self._online_threshold_ms:
                status = self.ONLINE
                reason = "Internet connection detected."
            elif response.status_code < 500:
                status = self.ONLINE
                reason = "Internet connection detected (higher latency)."
            else:
                reason = f"Connectivity probe failed with status {response.status_code}."
        except Exception as exc:
            reason = f"No internet connection detected ({exc.__class__.__name__})."

        with self._lock:
            self._status = status
            self._latency_ms = latency_ms
            self._checked_at = int(time.time())
            self._reason = reason

    def _loop(self) -> None:
        while True:
            self._probe_once()
            time.sleep(self._interval_secs)

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        thread = threading.Thread(target=self._loop, daemon=True)
        thread.start()

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            status = self._status
            latency_ms = self._latency_ms
            checked_at = self._checked_at
            reason = self._reason

        # cloud_available is capability at this moment (master+key+internet)
        cloud_available = self.cloud_master_enabled() and self.has_api_key() and status == self.ONLINE
        if self.cloud_master_enabled() and not self.has_api_key():
            reason = "Cloud is enabled but OPENAI_API_KEY is missing."

        return {
            "status": status,
            "latency_ms": latency_ms,
            "checked_at": checked_at,
            "cloud_available": cloud_available,
            "reason": reason,
        }


connectivity_manager = ConnectivityManager()

