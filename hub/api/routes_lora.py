"""
API routes for ESP+LoRa serial/Bluetooth monitoring and hub-to-hub messaging.
"""

import time
import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy.orm import Session

from hub.db.session import get_db
from hub.db import schema
from hub.core.lora_serial import get_lora_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lora", tags=["lora"])


# ── Request models ─────────────────────────────────────────────────────────

class ConnectRequest(BaseModel):
    port: str
    baud: int = 115200
    connection_type: str = "serial"  # "serial" or "bluetooth"


class SendRequest(BaseModel):
    target_hub_id: Optional[int] = None
    category_id: Optional[int] = None
    subject: str
    content: str
    priority: str = "normal"


class RawSendRequest(BaseModel):
    text: str


class AutoConnectRequest(BaseModel):
    enabled: bool


class EncryptionKeyRequest(BaseModel):
    key: Optional[str] = None  # hex string; omit to auto-generate


# ── REST endpoints ─────────────────────────────────────────────────────────

@router.get("/status")
def lora_status(db: Session = Depends(get_db)):
    mgr = get_lora_manager()
    status = mgr.get_status()
    # Include DB-persisted auto_connect flag
    try:
        cfg = db.query(schema.LoraConfig).first()
        status["auto_connect"] = bool(cfg.auto_connect) if cfg else False
    except Exception:
        status["auto_connect"] = False
    return status


@router.get("/ports")
def lora_ports():
    mgr = get_lora_manager()
    return {"ports": mgr.list_serial_ports()}


@router.post("/connect")
def lora_connect(req: ConnectRequest, db: Session = Depends(get_db)):
    mgr = get_lora_manager()

    _register_message_callback(mgr, db)

    result = mgr.connect(
        port=req.port,
        baud=req.baud,
        conn_type=req.connection_type,
    )

    if result.get("ok"):
        _save_lora_config(db, req.port, req.baud, req.connection_type)

    return result


@router.post("/disconnect")
def lora_disconnect(db: Session = Depends(get_db)):
    mgr = get_lora_manager()
    result = mgr.disconnect()
    return result


@router.post("/send")
def lora_send(req: SendRequest, db: Session = Depends(get_db)):
    mgr = get_lora_manager()

    this_hub = db.query(schema.Hub).first()
    source_hub_id = this_hub.hub_id if this_hub else None
    source_device_id = this_hub.device_id if this_hub else None

    payload = {
        "type": "msg",
        "from": source_device_id,
        "to": req.target_hub_id,
        "subject": req.subject,
        "content": req.content,
        "priority": req.priority,
    }

    result = mgr.send_message(payload)

    if result.get("ok"):
        now = int(time.time())
        msg = schema.HubMessage(
            category_id=req.category_id,
            source_hub_id=source_hub_id,
            target_hub_id=req.target_hub_id,
            subject=req.subject,
            content=req.content,
            priority=req.priority,
            status="pending",
            sent_at=now,
            received_via="lora",
            created_by="admin",
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        result["message_id"] = msg.id

    return result


class SendAckRequest(BaseModel):
    message_id: int  # The received message's DB ID


@router.post("/send_ack")
def lora_send_ack(req: SendAckRequest, db: Session = Depends(get_db)):
    """Send a lightweight ACK signal back to the sender — no new message row created."""
    mgr = get_lora_manager()

    # Look up the received message
    msg = db.query(schema.HubMessage).filter(schema.HubMessage.id == req.message_id).first()
    if not msg:
        return {"ok": False, "error": "Message not found"}

    # ALWAYS mark the local received message as "read" (operator acknowledged it)
    if msg.status == "pending":
        msg.status = "read"
        if not msg.received_at:
            msg.received_at = int(time.time())
        db.commit()

    this_hub = db.query(schema.Hub).first()
    source_device_id = this_hub.device_id if this_hub else None

    # Build lightweight ACK payload (type="ack" so the remote hub doesn't store it)
    payload = {
        "type": "ack",
        "from": source_device_id,
        "ack_subject": msg.subject or "",
        "ack_content": msg.content or "",
        "ack_msg_id": msg.id,
    }

    lora_result = mgr.send_message(payload)

    return {
        "ok": True,
        "ack_sent": lora_result.get("ok", False),
        "lora_error": lora_result.get("error") if not lora_result.get("ok") else None,
    }


class AutoConnectRequest(BaseModel):
    enabled: bool


@router.post("/auto-connect")
def lora_auto_connect(req: AutoConnectRequest, db: Session = Depends(get_db)):
    cfg = db.query(schema.LoraConfig).first()
    if not cfg:
        cfg = schema.LoraConfig(
            port="",
            baud_rate=115200,
            connection_type="serial",
            auto_connect=1 if req.enabled else 0,
            last_connected=int(time.time()),
        )
        db.add(cfg)
    else:
        cfg.auto_connect = 1 if req.enabled else 0
    db.commit()

    mgr = get_lora_manager()
    if req.enabled:
        mgr.enable_auto_reconnect()
    else:
        mgr.disable_auto_reconnect()

    return {"ok": True, "auto_connect": req.enabled}


@router.post("/send_raw")
def lora_send_raw(req: RawSendRequest):
    mgr = get_lora_manager()
    return mgr.send_raw(req.text)


@router.get("/log")
def lora_log(limit: int = 100):
    mgr = get_lora_manager()
    return {"lines": mgr.get_log(limit)}


@router.post("/auto-connect")
def lora_auto_connect(req: AutoConnectRequest, db: Session = Depends(get_db)):
    """Toggle auto-connect on/off. Persists to DB and enables/disables on the manager."""
    mgr = get_lora_manager()

    # Persist to DB
    try:
        cfg = db.query(schema.LoraConfig).first()
        if cfg:
            cfg.auto_connect = 1 if req.enabled else 0
        else:
            cfg = schema.LoraConfig(
                port="",
                baud_rate=115200,
                connection_type="serial",
                auto_connect=1 if req.enabled else 0,
                last_connected=int(time.time()),
            )
            db.add(cfg)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save auto-connect setting: {e}")

    # Enable/disable on the manager
    if req.enabled:
        mgr.enable_auto_reconnect()
    else:
        mgr.disable_auto_reconnect()

    return {"ok": True, "auto_connect": req.enabled}


# ── Encryption key management ──────────────────────────────────────────────

@router.get("/encryption")
def lora_encryption_status(db: Session = Depends(get_db)):
    """Return whether LoRa encryption is enabled and a masked key preview."""
    row = db.query(schema.StructuredConfig).filter(
        schema.StructuredConfig.key == "lora_encryption_key"
    ).first()
    if row and row.value:
        masked = row.value[:6] + "..." + row.value[-4:]
        return {"enabled": True, "key_preview": masked, "key_length": len(row.value), "key_source": "database"}

    # Fallback: environment/.env key via manager helper
    mgr = get_lora_manager()
    env_key = mgr._get_encryption_key()
    if env_key:
        masked = env_key[:6] + "..." + env_key[-4:]
        return {"enabled": True, "key_preview": masked, "key_length": len(env_key), "key_source": "environment"}

    return {"enabled": False, "key_preview": None, "key_length": 0, "key_source": None}


@router.post("/encryption")
def lora_encryption_set(req: EncryptionKeyRequest, db: Session = Depends(get_db)):
    """Set or generate a new LoRa encryption key. All hubs must share the same key."""
    from hub.core.crypto import generate_key, CRYPTO_AVAILABLE
    if not CRYPTO_AVAILABLE:
        return {"ok": False, "error": "cryptography package is not installed on this hub"}

    key_hex = req.key if req.key else generate_key()

    try:
        bytes.fromhex(key_hex)
    except ValueError:
        return {"ok": False, "error": "Key must be a valid hex string"}
    if len(bytes.fromhex(key_hex)) != 32:
        return {"ok": False, "error": "Key must be exactly 32 bytes (64 hex characters)"}

    row = db.query(schema.StructuredConfig).filter(
        schema.StructuredConfig.key == "lora_encryption_key"
    ).first()
    if row:
        row.value = key_hex
    else:
        row = schema.StructuredConfig(key="lora_encryption_key", value=key_hex)
        db.add(row)
    db.commit()

    logger.info("LoRa encryption key updated")
    return {"ok": True, "key": key_hex}


@router.delete("/encryption")
def lora_encryption_disable(db: Session = Depends(get_db)):
    """Remove the encryption key, disabling LoRa message encryption."""
    row = db.query(schema.StructuredConfig).filter(
        schema.StructuredConfig.key == "lora_encryption_key"
    ).first()
    if row:
        db.delete(row)
        db.commit()
        logger.info("LoRa encryption disabled (key removed)")
    return {"ok": True, "enabled": False}


# ── WebSocket for real-time serial monitor ─────────────────────────────────

@router.websocket("/ws/lora")
async def ws_lora(websocket: WebSocket):
    await websocket.accept()
    mgr = get_lora_manager()

    queue = asyncio.Queue(maxsize=200)
    mgr.add_ws_listener(queue)

    try:
        for line in mgr.get_log(50):
            await websocket.send_text(line)

        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_text(msg)
            except asyncio.TimeoutError:
                await websocket.send_text("")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"LoRa WS closed: {e}")
    finally:
        mgr.remove_ws_listener(queue)


# ── Helpers ────────────────────────────────────────────────────────────────

def _register_message_callback(mgr, db_session: Session):
    """No-op -- DB persistence is now handled directly inside LoRaSerialManager._save_received_message.
    Kept for API compatibility if custom callbacks are needed later."""
    pass


def _save_lora_config(db: Session, port: str, baud: int, conn_type: str):
    """Persist the last-used connection settings."""
    try:
        existing = db.query(schema.LoraConfig).first()
        if existing:
            existing.port = port
            existing.baud_rate = baud
            existing.connection_type = conn_type
            existing.last_connected = int(time.time())
        else:
            cfg = schema.LoraConfig(
                port=port,
                baud_rate=baud,
                connection_type=conn_type,
                auto_connect=1,
                last_connected=int(time.time()),
            )
            db.add(cfg)
        db.commit()
    except Exception as e:
        logger.warning(f"Could not save LoRa config: {e}")


def startup_auto_connect():
    """Called on app startup -- reconnect if auto_connect is enabled (USB serial only)."""
    from hub.db.session import SessionLocal
    db = SessionLocal()
    try:
        cfg = db.query(schema.LoraConfig).first()
        if cfg and cfg.auto_connect:
            mgr = get_lora_manager()
            _register_message_callback(mgr, db)

            mgr._auto_reconnect_enabled = True
            mgr._last_baud = cfg.baud_rate or 115200
            mgr._last_conn_type = cfg.connection_type or "serial"
            mgr._last_port = cfg.port

            usb_ports = mgr.list_usb_serial_ports()
            if not usb_ports:
                logger.warning("LoRa auto-connect: no USB serial device found, starting background scan")
                mgr._start_auto_reconnect()
                return

            # Try saved port if it's a USB device
            if cfg.port and any(p["port"] == cfg.port for p in usb_ports):
                result = mgr.connect(
                    port=cfg.port,
                    baud=cfg.baud_rate,
                    conn_type=cfg.connection_type,
                )
                if result.get("ok"):
                    logger.info(f"LoRa auto-connected to {cfg.port}")
                    return

            # Saved port unavailable — try other USB serial ports
            logger.warning(f"LoRa auto-connect to {cfg.port} failed, scanning USB ports...")
            for p in usb_ports:
                port_name = p["port"]
                if port_name == cfg.port:
                    continue
                result = mgr.connect(
                    port=port_name,
                    baud=cfg.baud_rate or 115200,
                    conn_type=cfg.connection_type or "serial",
                )
                if result.get("ok"):
                    logger.info(f"LoRa auto-connected to {port_name} (fallback)")
                    _save_lora_config(db, port_name, cfg.baud_rate or 115200, cfg.connection_type or "serial")
                    return

            logger.warning("LoRa auto-connect: USB ports found but connect failed, starting background reconnect")
            mgr._start_auto_reconnect()
    except Exception as e:
        logger.debug(f"LoRa auto-connect skipped: {e}")
    finally:
        db.close()
