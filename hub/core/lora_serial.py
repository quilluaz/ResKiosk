"""
Singleton manager for ESP+LoRa serial/Bluetooth communication.

Handles port scanning, connect/disconnect, background reading,
and message send/receive over Serial USB or Bluetooth serial.
"""

import json
import threading
import time
import logging
from pathlib import Path
from collections import deque
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not installed — LoRa serial features disabled")


class LoRaSerialManager:
    """Thread-safe singleton that bridges the Hub to an ESP+LoRa module."""

    _instance: Optional["LoRaSerialManager"] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False

        self.connection_type: Optional[str] = None  # "serial" or "bluetooth"
        self.port_name: Optional[str] = None
        self.baud_rate: int = 115200
        self.connected: bool = False
        self.last_activity: Optional[float] = None
        self.device_info: Optional[str] = None

        self.messages_sent: int = 0
        self.messages_received: int = 0

        self._log_buffer: deque = deque(maxlen=500)
        self._ws_listeners: list = []
        self._ws_lock = threading.Lock()

        self._on_message_callback = None

        # Auto-reconnect state
        self._auto_reconnect_enabled: bool = False
        self._auto_reconnect_thread: Optional[threading.Thread] = None
        self._auto_reconnect_running: bool = False
        self._last_port: Optional[str] = None
        self._last_baud: int = 115200
        self._last_conn_type: str = "serial"

    # ── Port scanning ──────────────────────────────────────────────────────

    _USB_KEYWORDS = ("USB", "CH340", "CH341", "CP210", "FTDI", "PL2303", "ACM", "Arduino")

    @staticmethod
    def list_serial_ports() -> List[Dict[str, str]]:
        if not SERIAL_AVAILABLE:
            return []
        ports = serial.tools.list_ports.comports()
        return [
            {
                "port": p.device,
                "description": p.description,
                "hwid": p.hwid,
            }
            for p in sorted(ports, key=lambda x: x.device)
        ]

    @classmethod
    def list_usb_serial_ports(cls) -> List[Dict[str, str]]:
        """Return only ports whose description or hwid indicate a USB serial adapter."""
        all_ports = cls.list_serial_ports()
        return [
            p for p in all_ports
            if any(kw in (p.get("description", "") + " " + p.get("hwid", "")).upper()
                   for kw in cls._USB_KEYWORDS)
        ]

    # ── Connection ─────────────────────────────────────────────────────────

    def connect(
        self,
        port: str,
        baud: int = 115200,
        conn_type: str = "serial",
    ) -> Dict[str, Any]:
        if not SERIAL_AVAILABLE:
            return {"ok": False, "error": "pyserial is not installed"}

        if self.connected:
            self.disconnect()

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baud,
                timeout=1,
                write_timeout=2,
            )
            self.connected = True
            self.connection_type = conn_type
            self.port_name = port
            self.baud_rate = baud
            self.last_activity = time.time()
            self.device_info = None

            # Remember last-known settings for auto-reconnect
            self._last_port = port
            self._last_baud = baud
            self._last_conn_type = conn_type

            # Stop any running auto-reconnect loop (we are connected now)
            self._auto_reconnect_running = False

            self._running = True
            self._reader_thread = threading.Thread(
                target=self._read_loop, daemon=True, name="lora-reader"
            )
            self._reader_thread.start()

            self._log(f"[SYS] Connected to {port} @ {baud} baud ({conn_type})")
            logger.info(f"LoRa: connected to {port} @ {baud} ({conn_type})")
            return {"ok": True}

        except Exception as e:
            self.connected = False
            self._serial = None
            err = str(e)
            self._log(f"[ERR] Connection failed: {err}")
            logger.error(f"LoRa connect error: {err}")
            return {"ok": False, "error": err}

    def disconnect(self) -> Dict[str, Any]:
        self._running = False
        if self._serial and self._serial.is_open:
            try:
                self._serial.close()
            except Exception:
                pass
        self._serial = None
        self.connected = False
        prev_port = self.port_name
        self.port_name = None
        self.connection_type = None
        self.device_info = None
        self._log(f"[SYS] Disconnected from {prev_port or 'device'}")
        logger.info("LoRa: disconnected")
        return {"ok": True}

    # ── Encryption helpers ─────────────────────────────────────────────────

    @staticmethod
    def _get_encryption_key() -> Optional[str]:
        """Read the LoRa encryption key from StructuredConfig, env, or local .env file."""
        # First try database (preferred - allows per-hub configuration)
        try:
            from hub.db.session import SessionLocal
            from hub.db import schema
            db = SessionLocal()
            try:
                row = db.query(schema.StructuredConfig).filter(
                    schema.StructuredConfig.key == "lora_encryption_key"
                ).first()
                if row and row.value:
                    return row.value
            finally:
                db.close()
        except Exception as e:
            logger.debug(f"Could not read encryption key from database: {e}")
        
        # Fallback to environment variable
        import os
        env_key = os.environ.get("LORA_ENCRYPTION_KEY")
        if env_key:
            logger.debug("Using encryption key from environment variable")
            return env_key.strip()

        # Last fallback: parse workspace/root .env (for launches that don't export env vars)
        try:
            repo_root = Path(__file__).resolve().parents[2]
            env_path = repo_root / ".env"
            if env_path.exists():
                for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    if key.strip() == "LORA_ENCRYPTION_KEY":
                        # Strip inline comment and optional quotes
                        cleaned = value.split("#", 1)[0].strip().strip('"').strip("'")
                        if cleaned:
                            logger.debug("Using encryption key from .env file")
                            return cleaned
        except Exception as e:
            logger.debug(f"Could not read encryption key from .env: {e}")

        return None

    # ── Sending ────────────────────────────────────────────────────────────

    def send_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.connected or not self._serial or not self._serial.is_open:
            return {"ok": False, "error": "Not connected to any device"}

        enc_key = self._get_encryption_key()
        if enc_key:
            try:
                from hub.core.crypto import encrypt_payload
                wire_payload = encrypt_payload(payload, enc_key)
                self._log("[SYS] Encrypting outbound message")
            except Exception as e:
                logger.error(f"Encryption failed; blocking plaintext send: {e}")
                self._log(f"[ERR] Encryption failed: {e}")
                return {
                    "ok": False,
                    "error": (
                        "Encryption failed; message blocked to prevent plaintext transmission. "
                        "Verify cryptography is installed and key is valid."
                    ),
                }
        else:
            wire_payload = payload

        line = json.dumps(wire_payload, separators=(",", ":")) + "\n"
        try:
            self._serial.write(line.encode("utf-8"))
            self._serial.flush()
            self.messages_sent += 1
            self.last_activity = time.time()
            self._log(f"[TX] {line.strip()}")
            return {"ok": True}
        except Exception as e:
            err = str(e)
            self._log(f"[ERR] Send failed: {err}")
            logger.error(f"LoRa send error: {err}")
            return {"ok": False, "error": err}

    def send_raw(self, text: str) -> Dict[str, Any]:
        """Send a raw string (for AT commands or debugging)."""
        if not self.connected or not self._serial or not self._serial.is_open:
            return {"ok": False, "error": "Not connected to any device"}
        try:
            data = text if text.endswith("\n") else text + "\n"
            self._serial.write(data.encode("utf-8"))
            self._serial.flush()
            self.last_activity = time.time()
            self._log(f"[TX] {text.strip()}")
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── Background reader ──────────────────────────────────────────────────

    def _read_loop(self):
        while self._running and self._serial and self._serial.is_open:
            try:
                raw = self._serial.readline()
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                self.last_activity = time.time()
                self._log(f"[RX] {line}")

                self._try_parse_message(line)

            except serial.SerialException as e:
                self._log(f"[ERR] Serial read error: {e}")
                logger.error(f"LoRa read error: {e}")
                self._running = False
                self.connected = False
                self.port_name = None
                self.connection_type = None
                # Trigger auto-reconnect if enabled
                if self._auto_reconnect_enabled:
                    self._start_auto_reconnect()
                break
            except Exception as e:
                self._log(f"[ERR] Read loop error: {e}")

        if not self._running:
            self._log("[SYS] Reader thread stopped")

    def _try_parse_message(self, line: str):
        """Attempt to parse a JSON-line LoRa message and save to DB.

        The ESP prefixes incoming data with [RX] and echoes sent data
        with [TX USB] / [TX]. We only process [RX]-prefixed lines.
        Encrypted envelopes (type=="enc") are decrypted before processing.
        """
        prefix = line.split("{")[0].strip().upper()
        if prefix.startswith("[TX"):
            return

        brace = line.find("{")
        if brace == -1:
            return
        json_str = line[brace:]

        try:
            data = json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            return

        # Decrypt if this is an encrypted envelope
        from hub.core.crypto import is_encrypted
        if is_encrypted(data):
            enc_key = self._get_encryption_key()
            if not enc_key:
                self._log("[ERR] Received encrypted message but no decryption key configured")
                logger.warning("Encrypted LoRa message received but no key is set")
                return
            from hub.core.crypto import decrypt_payload
            data = decrypt_payload(data, enc_key)
            if data is None:
                self._log("[ERR] Failed to decrypt incoming message (bad key or corrupted)")
                logger.error("LoRa message decryption failed")
                return
            self._log("[SYS] Decrypted incoming message")

        msg_type = data.get("type")
        if msg_type == "msg":
            self.messages_received += 1
            self._save_received_message(data)
            if self._on_message_callback:
                try:
                    self._on_message_callback(data)
                except Exception as e:
                    logger.error(f"LoRa message callback error: {e}")

        elif msg_type == "ack":
            self._handle_ack(data)

        elif msg_type == "info":
            self.device_info = data.get("firmware", data.get("device", str(data)))
            self._log(f"[SYS] Device info: {self.device_info}")

    @staticmethod
    def _resolve_hub_by_device_id(db, device_id):
        """Look up a hub by device_id; auto-register if unknown."""
        from hub.db import schema
        if not device_id:
            return None
        hub = db.query(schema.Hub).filter(schema.Hub.device_id == str(device_id)).first()
        if hub:
            return hub.hub_id
        import time as _time
        new_hub = schema.Hub(
            device_id=str(device_id),
            hub_name=f"Hub-{device_id}",
            location="Unknown",
            created_at=int(_time.time()),
        )
        db.add(new_hub)
        db.commit()
        db.refresh(new_hub)
        logger.info(f"Auto-registered new hub: {new_hub.hub_name} (device_id={device_id})")
        return new_hub.hub_id

    def _save_received_message(self, data: dict):
        """Persist an incoming LoRa message to the hub_messages table."""
        try:
            from hub.db.session import SessionLocal
            from hub.db import schema

            db = SessionLocal()
            try:
                now = int(time.time())
                source_hub_id = self._resolve_hub_by_device_id(db, data.get("from"))
                msg = schema.HubMessage(
                    category_id=None,
                    source_hub_id=source_hub_id,
                    target_hub_id=data.get("to"),
                    subject=data.get("subject", ""),
                    content=data.get("content", ""),
                    priority=data.get("priority", "normal"),
                    status="pending",
                    sent_at=data.get("sent_at", now),
                    received_at=now,
                    received_via="lora",
                    created_by="lora-rx",
                    hop_count=data.get("hop_count"),
                    ttl=data.get("ttl"),
                )
                db.add(msg)
                db.commit()
                self._log(f"[SYS] Message saved to database (id={msg.id})")
                logger.info(f"LoRa RX message stored: {msg.id}")

                source_hub_name = None
                if source_hub_id:
                    src = db.query(schema.Hub).filter(
                        schema.Hub.hub_id == source_hub_id
                    ).first()
                    source_hub_name = src.hub_name if src else None

                self._broadcast_ws(json.dumps({
                    "event": "new_message",
                    "id": msg.id,
                    "subject": msg.subject,
                    "content": msg.content,
                    "priority": msg.priority,
                    "source_hub_id": msg.source_hub_id,
                    "source_hub_name": source_hub_name,
                    "from_device_id": data.get("from"),
                    "received_via": "lora",
                }))
            except Exception as e:
                logger.error(f"Failed to store LoRa RX message: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"DB import error in LoRa save: {e}")

    # ── ACK handling ───────────────────────────────────────────────────────

    def _handle_ack(self, data: dict):
        """Process an incoming ACK: update the original sent message status to 'delivered'."""
        ack_subject = data.get("ack_subject", "")
        ack_content = data.get("ack_content", "")
        ack_msg_id = data.get("ack_msg_id")
        from_device = data.get("from")

        self._log(f"[SYS] ACK received for: {ack_subject or ack_msg_id} from {from_device}")
        logger.info(f"LoRa ACK received — subject={ack_subject!r}, msg_id={ack_msg_id}, from={from_device}")

        try:
            from hub.db.session import SessionLocal
            from hub.db import schema

            db = SessionLocal()
            try:
                now = int(time.time())

                # Determine this hub's ID (try HubIdentity first, then Hub table)
                this_hub_id = None
                try:
                    identity = db.query(schema.HubIdentity).first()
                    if identity and identity.hub_id:
                        this_hub_id = identity.hub_id
                except Exception:
                    pass
                if not this_hub_id:
                    this_hub = db.query(schema.Hub).first()
                    this_hub_id = this_hub.hub_id if this_hub else None

                # Strip "ACK: " prefix if present (backward compat)
                clean_subject = ack_subject
                if clean_subject.startswith("ACK: "):
                    clean_subject = clean_subject[5:]

                msg = None

                # Strategy 1: match by subject + source hub + pending status
                if clean_subject and this_hub_id:
                    msg = (
                        db.query(schema.HubMessage)
                        .filter(
                            schema.HubMessage.source_hub_id == this_hub_id,
                            schema.HubMessage.subject == clean_subject,
                            schema.HubMessage.status.in_(["pending", "sent"]),
                        )
                        .order_by(schema.HubMessage.sent_at.desc())
                        .first()
                    )

                # Strategy 2: relax status filter (maybe status was changed manually)
                if not msg and clean_subject and this_hub_id:
                    msg = (
                        db.query(schema.HubMessage)
                        .filter(
                            schema.HubMessage.source_hub_id == this_hub_id,
                            schema.HubMessage.subject == clean_subject,
                            schema.HubMessage.status != "delivered",
                        )
                        .order_by(schema.HubMessage.sent_at.desc())
                        .first()
                    )
                    if msg:
                        self._log(f"[SYS] ACK matched via fallback (status was '{msg.status}')")

                # Strategy 3: match by subject only (no hub filter)
                if not msg and clean_subject:
                    msg = (
                        db.query(schema.HubMessage)
                        .filter(
                            schema.HubMessage.subject == clean_subject,
                            schema.HubMessage.status.in_(["pending", "sent"]),
                            schema.HubMessage.received_via == "lora",
                        )
                        .order_by(schema.HubMessage.sent_at.desc())
                        .first()
                    )
                    if msg:
                        self._log(f"[SYS] ACK matched via subject-only fallback")

                # Strategy 4: match by message body/content (subject didn't match)
                if not msg and ack_content:
                    msg = (
                        db.query(schema.HubMessage)
                        .filter(
                            schema.HubMessage.content == ack_content,
                            schema.HubMessage.status.in_(["pending", "sent"]),
                            schema.HubMessage.received_via == "lora",
                        )
                        .order_by(schema.HubMessage.sent_at.desc())
                        .first()
                    )
                    if msg:
                        self._log(f"[SYS] ACK matched via message body fallback")

                if msg:
                    msg.status = "delivered"
                    if not msg.received_at:
                        msg.received_at = now
                    db.commit()
                    self._log(f"[SYS] Message #{msg.id} status → delivered")
                    logger.info(f"Message {msg.id} marked as delivered via ACK")

                    # Notify console via WebSocket
                    self._broadcast_ws(json.dumps({
                        "event": "message_delivered",
                        "id": msg.id,
                        "status": "delivered",
                    }))
                else:
                    self._log(f"[SYS] ACK received but no matching message found for subject: '{clean_subject}' (hub_id={this_hub_id})")
                    logger.warning(f"ACK could not be matched — subject={clean_subject!r}, hub_id={this_hub_id}")

            except Exception as e:
                logger.error(f"Failed to process ACK: {e}")
                db.rollback()
            finally:
                db.close()
        except Exception as e:
            logger.error(f"DB import error in ACK handler: {e}")

    # ── Logging / WebSocket broadcast ──────────────────────────────────────

    def _log(self, text: str):
        ts = time.strftime("%H:%M:%S")
        entry = f"[{ts}] {text}"
        self._log_buffer.append(entry)
        self._broadcast_ws(entry)

    def _broadcast_ws(self, text: str):
        with self._ws_lock:
            dead = []
            for q in self._ws_listeners:
                try:
                    q.put_nowait(text)
                except Exception:
                    dead.append(q)
            for q in dead:
                self._ws_listeners.remove(q)

    def add_ws_listener(self, queue):
        with self._ws_lock:
            self._ws_listeners.append(queue)

    def remove_ws_listener(self, queue):
        with self._ws_lock:
            try:
                self._ws_listeners.remove(queue)
            except ValueError:
                pass

    def get_log(self, limit: int = 100) -> List[str]:
        return list(self._log_buffer)[-limit:]

    # ── Status ─────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "connection_type": self.connection_type,
            "port": self.port_name,
            "baud_rate": self.baud_rate,
            "device_info": self.device_info,
            "last_activity": self.last_activity,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "serial_available": SERIAL_AVAILABLE,
            "auto_reconnect": self._auto_reconnect_enabled,
        }

    def set_on_message(self, callback):
        self._on_message_callback = callback

    # ── Auto-reconnect ─────────────────────────────────────────────────────

    def enable_auto_reconnect(self):
        """Enable auto-reconnect. If currently disconnected, start trying."""
        self._auto_reconnect_enabled = True
        self._log("[SYS] Auto-reconnect enabled")
        logger.info("LoRa: auto-reconnect enabled")
        if not self.connected:
            self._start_auto_reconnect()

    def disable_auto_reconnect(self):
        """Disable auto-reconnect and stop the reconnect loop."""
        self._auto_reconnect_enabled = False
        self._auto_reconnect_running = False
        self._log("[SYS] Auto-reconnect disabled")
        logger.info("LoRa: auto-reconnect disabled")

    def _start_auto_reconnect(self):
        """Spin up the background auto-reconnect thread if not already running."""
        if self._auto_reconnect_running:
            return
        self._auto_reconnect_running = True
        self._auto_reconnect_thread = threading.Thread(
            target=self._auto_reconnect_loop, daemon=True, name="lora-auto-reconnect"
        )
        self._auto_reconnect_thread.start()

    def _is_usb_port(self, port_name: str) -> bool:
        """Check if a port name corresponds to a known USB serial device."""
        usb_ports = self.list_usb_serial_ports()
        return any(p["port"] == port_name for p in usb_ports)

    def _try_connect_and_verify(self, port: str, baud: int, conn_type: str) -> bool:
        """Connect and verify the connection stays alive for a short period."""
        result = self.connect(port=port, baud=baud, conn_type=conn_type)
        if not result.get("ok"):
            return False
        time.sleep(1.5)
        if self.connected and self._serial and self._serial.is_open:
            return True
        return False

    def _auto_reconnect_loop(self):
        """Background loop: try reconnecting every 5 seconds (USB serial only)."""
        self._log("[SYS] Auto-reconnect: searching for USB serial device...")
        attempt = 0
        no_device_alerted = False

        while self._auto_reconnect_running and self._auto_reconnect_enabled and not self.connected:
            attempt += 1

            usb_ports = self.list_usb_serial_ports()

            if not usb_ports:
                if not no_device_alerted:
                    self._log("[SYS] Auto-reconnect: no USB serial device found. Plug in your Relay module.")
                    self._broadcast_ws(json.dumps({
                        "event": "no_usb_device",
                        "message": "No USB serial device detected. Please plug in your Relay module.",
                    }))
                    no_device_alerted = True
            else:
                no_device_alerted = False

                # 1. Try last-known port if it's among current USB ports
                if self._last_port and any(p["port"] == self._last_port for p in usb_ports):
                    if self._try_connect_and_verify(
                        self._last_port, self._last_baud, self._last_conn_type
                    ):
                        self._log(f"[SYS] Auto-reconnect: restored connection to {self._last_port}")
                        self._auto_reconnect_running = False
                        return

                # 2. Try remaining USB serial ports
                for p in usb_ports:
                    if not self._auto_reconnect_running or not self._auto_reconnect_enabled:
                        break
                    port_name = p["port"]
                    if port_name == self._last_port:
                        continue
                    if self._try_connect_and_verify(
                        port_name, self._last_baud or 115200, self._last_conn_type or "serial"
                    ):
                        self._log(f"[SYS] Auto-reconnect: connected to {port_name}")
                        self._auto_reconnect_running = False
                        return

            if attempt % 6 == 0:
                self._log(f"[SYS] Auto-reconnect: still searching... (attempt {attempt})")

            for _ in range(50):  # 5 seconds, interruptible
                if not self._auto_reconnect_running or not self._auto_reconnect_enabled or self.connected:
                    break
                time.sleep(0.1)

        self._auto_reconnect_running = False
        if self.connected:
            self._log("[SYS] Auto-reconnect: connection restored")
        else:
            self._log("[SYS] Auto-reconnect: stopped")


def get_lora_manager() -> LoRaSerialManager:
    return LoRaSerialManager()
