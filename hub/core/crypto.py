"""
AES-256-GCM encryption for hub-to-hub LoRa messages.

All hubs in a network share a single pre-shared key (PSK).  When a key is
configured, outbound payloads are encrypted into a compact envelope before
serial transmission.  Inbound envelopes are decrypted back to the original
JSON dict on receipt.

Wire format:  {"type":"enc","d":"<base64(IV ‖ ciphertext ‖ tag)>"}
  IV        = 12 bytes  (random per message)
  tag       = 16 bytes  (GCM authentication tag)
  ciphertext = variable (the original JSON payload)
"""

import base64
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography package not installed — LoRa encryption unavailable")

_IV_LEN = 12
_TAG_LEN = 16
_KEY_BITS = 256
_KEY_BYTES = _KEY_BITS // 8


def generate_key() -> str:
    """Return a new random 256-bit key as a hex string (64 hex chars)."""
    return os.urandom(_KEY_BYTES).hex()


def _hex_to_bytes(key_hex: str) -> bytes:
    raw = bytes.fromhex(key_hex)
    if len(raw) != _KEY_BYTES:
        raise ValueError(f"Key must be {_KEY_BYTES} bytes ({_KEY_BITS}-bit), got {len(raw)}")
    return raw


def encrypt_payload(payload: Dict[str, Any], key_hex: str) -> Dict[str, str]:
    """Encrypt a full message payload dict into an envelope dict.

    Returns ``{"type": "enc", "d": "<base64>"}`` suitable for JSON
    serialisation and serial transmission.
    """
    if not CRYPTO_AVAILABLE:
        raise RuntimeError("cryptography package is not installed")

    key = _hex_to_bytes(key_hex)
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    iv = os.urandom(_IV_LEN)
    aesgcm = AESGCM(key)
    ciphertext_and_tag = aesgcm.encrypt(iv, plaintext, None)

    blob = iv + ciphertext_and_tag  # IV ‖ ciphertext ‖ tag
    return {"type": "enc", "d": base64.b64encode(blob).decode("ascii")}


def decrypt_payload(envelope: Dict[str, str], key_hex: str) -> Optional[Dict[str, Any]]:
    """Decrypt an encrypted envelope back to the original payload dict.

    Returns ``None`` on any failure (bad key, tampered data, missing lib).
    """
    if not CRYPTO_AVAILABLE:
        logger.error("Cannot decrypt: cryptography package not installed")
        return None

    try:
        key = _hex_to_bytes(key_hex)
        blob = base64.b64decode(envelope["d"])

        if len(blob) < _IV_LEN + _TAG_LEN:
            logger.error("Encrypted blob too short")
            return None

        iv = blob[:_IV_LEN]
        ciphertext_and_tag = blob[_IV_LEN:]

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(iv, ciphertext_and_tag, None)
        return json.loads(plaintext)

    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None


def is_encrypted(data: dict) -> bool:
    """Return True if *data* looks like an encrypted envelope."""
    return data.get("type") == "enc" and "d" in data
