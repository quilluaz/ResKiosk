import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models.api_models import EmergencyRequest, EmergencyResolveRequest, EmergencyStatusResponse
import asyncio
import json
import logging
from fastapi.responses import StreamingResponse

router = APIRouter()
log = logging.getLogger(__name__)

# Active SSE subscribers — one entry per open console browser tab
_subscribers: list[asyncio.Queue] = []


async def _broadcast(event: dict):
    data = f"data: {json.dumps(event)}\n\n"
    dead = []
    for q in _subscribers:
        try:
            q.put_nowait(data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        _subscribers.remove(q)


def _alert_to_dict(alert: schema.EmergencyAlert, db: Session) -> dict:
    """Build alert dict; join kiosk table for kiosk_name, fall back to kiosk_location."""
    kiosk = db.query(schema.Kiosk).filter(schema.Kiosk.kiosk_id == alert.kiosk_id).first()
    display_name = (kiosk.kiosk_name or alert.kiosk_location) if kiosk else alert.kiosk_location
    return {
        "id": alert.id,
        "kiosk_id": alert.kiosk_id,
        "kiosk_location": alert.kiosk_location,
        "kiosk_name": display_name,
        "transcript": alert.transcript,
        "language": alert.language,
        "timestamp": alert.timestamp,
        "status": alert.status or ("RESOLVED" if alert.resolved else "ACTIVE"),
        "tier": alert.tier or 1,
        "alert_id_local": alert.alert_id_local,
        "acknowledged_at": alert.acknowledged_at,
        "responding_at": alert.responding_at,
        "dismissed_by_kiosk": alert.dismissed_by_kiosk,
        "dismissed_at": alert.dismissed_at,
        "resolution_notes": alert.resolution_notes,
        "resolved_by": alert.resolved_by,
        "resolved_at": alert.resolved_at,
        "retry_count": alert.retry_count,
    }


@router.post("/emergency")
async def receive_emergency(payload: EmergencyRequest, db: Session = Depends(get_db)):
    # Resolve hub_id from the Hub table if not provided
    hub_id = payload.hub_id
    if not hub_id:
        hub_row = db.query(schema.Hub).first()
        if hub_row:
            hub_id = str(hub_row.hub_id)

    # Deduplicate by kiosk-generated UUID
    if payload.alert_id_local:
        existing = (
            db.query(schema.EmergencyAlert)
            .filter(schema.EmergencyAlert.alert_id_local == payload.alert_id_local)
            .first()
        )
        if existing:
            event = _alert_to_dict(existing, db)
            return {"status": "received", "alert_id": existing.id, "alert": event}

    alert = schema.EmergencyAlert(
        kiosk_id=payload.kiosk_id,
        kiosk_location=payload.kiosk_location,
        hub_id=hub_id,
        transcript=payload.transcript or "",
        language=payload.language,
        timestamp=payload.timestamp or int(time.time() * 1000),
        resolved=0,
        status="ACTIVE",
        tier=payload.tier or 1,
        alert_id_local=payload.alert_id_local,
        retry_count=payload.retry_count or 0,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    event = _alert_to_dict(alert, db)
    event["type"] = "EMERGENCY_ALERT"
    event["alert_id"] = alert.id
    await _broadcast(event)

    log.warning(f"EMERGENCY from {alert.kiosk_id} @ {alert.kiosk_location}: {alert.transcript}")
    return {"status": "received", "alert_id": alert.id, "alert": event}


@router.get("/emergency/stream")
async def emergency_sse():
    """Console subscribes here. One long-lived connection per browser tab. Sends heartbeat every 30s."""
    q: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.append(q)

    async def generator():
        try:
            yield "data: {\"type\": \"CONNECTED\"}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield "data: {\"type\": \"HEARTBEAT\"}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            try:
                _subscribers.remove(q)
            except ValueError:
                pass

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/emergency/active")
def get_active_emergencies(db: Session = Depends(get_db)):
    alerts = (
        db.query(schema.EmergencyAlert)
        .filter(schema.EmergencyAlert.status != "RESOLVED")
        .order_by(schema.EmergencyAlert.tier.asc(), schema.EmergencyAlert.timestamp.desc())
        .all()
    )
    return {"alerts": [_alert_to_dict(a, db) for a in alerts]}


@router.post("/emergency/{alert_id}/resolve")
async def resolve_emergency(alert_id: int, payload: EmergencyResolveRequest, db: Session = Depends(get_db)):
    alert = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.id == alert_id).first()
    if alert:
        alert.status = "RESOLVED"
        alert.resolved = 1
        alert.resolved_at = int(time.time() * 1000)
        alert.resolution_notes = payload.resolution_notes
        alert.resolved_by = payload.resolved_by
        db.commit()
        event = _alert_to_dict(alert, db)
        event["type"] = "EMERGENCY_RESOLVED"
        event["alert_id"] = alert.id
        await _broadcast(event)
    return {"status": "resolved"}


@router.patch("/emergency/{alert_id}/acknowledge")
async def acknowledge_emergency(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.id == alert_id).first()
    if alert:
        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_at = int(time.time() * 1000)
        db.commit()
        event = _alert_to_dict(alert, db)
        event["type"] = "EMERGENCY_ACKNOWLEDGED"
        event["alert_id"] = alert.id
        await _broadcast(event)
    return {"status": "acknowledged"}


@router.patch("/emergency/{alert_id}/responding")
async def responding_emergency(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.id == alert_id).first()
    if alert:
        alert.status = "RESPONDING"
        alert.responding_at = int(time.time() * 1000)
        db.commit()
        event = _alert_to_dict(alert, db)
        event["type"] = "EMERGENCY_RESPONDING"
        event["alert_id"] = alert.id
        await _broadcast(event)
    return {"status": "responding"}


@router.patch("/emergency/{alert_id}/dismiss")
async def dismiss_emergency(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.id == alert_id).first()
    if alert:
        alert.status = "DISMISSED"
        alert.dismissed_by_kiosk = 1
        alert.dismissed_at = int(time.time() * 1000)
        db.commit()
        event = _alert_to_dict(alert, db)
        event["type"] = "EMERGENCY_DISMISSED"
        event["alert_id"] = alert.id
        await _broadcast(event)
    return {"status": "dismissed"}


@router.get("/emergency/{alert_id}/status", response_model=EmergencyStatusResponse)
def emergency_status(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.id == alert_id).first()
    if not alert:
        return {
            "id": alert_id,
            "status": "UNKNOWN",
            "acknowledged_at": None,
            "responding_at": None,
            "dismissed_at": None,
            "dismissed_by_kiosk": None,
            "resolved_at": None,
        }
    return {
        "id": alert.id,
        "status": alert.status or ("RESOLVED" if alert.resolved else "ACTIVE"),
        "acknowledged_at": alert.acknowledged_at,
        "responding_at": alert.responding_at,
        "dismissed_at": alert.dismissed_at,
        "dismissed_by_kiosk": alert.dismissed_by_kiosk,
        "resolved_at": alert.resolved_at,
    }


@router.get("/emergency/history")
def emergency_history(
    db: Session = Depends(get_db),
    kiosk_id: str | None = None,
    tier: int | None = None,
    ts_from: int | None = None,
    ts_to: int | None = None,
    limit: int = 100,
    offset: int = 0,
):
    q = db.query(schema.EmergencyAlert).filter(schema.EmergencyAlert.status == "RESOLVED")
    if kiosk_id:
        q = q.filter(schema.EmergencyAlert.kiosk_id == kiosk_id)
    if tier:
        q = q.filter(schema.EmergencyAlert.tier == tier)
    if ts_from:
        q = q.filter(schema.EmergencyAlert.timestamp >= ts_from)
    if ts_to:
        q = q.filter(schema.EmergencyAlert.timestamp <= ts_to)
    rows = q.order_by(schema.EmergencyAlert.timestamp.desc()).offset(offset).limit(limit).all()
    return {"alerts": [_alert_to_dict(a, db) for a in rows], "limit": limit, "offset": offset}
