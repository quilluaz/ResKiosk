import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.core.change_tracker import log_change
from hub.models.api_models import (
    MessageCreate, MessageUpdate, MessageResponse,
    CategoryResponse, HubResponse,
)

router = APIRouter()


def _msg_to_response(msg: schema.HubMessage, db: Session) -> dict:
    """Build MessageResponse dict with joined hub/category names."""
    cat = db.query(schema.Category).filter(
        schema.Category.category_id == msg.category_id
    ).first() if msg.category_id else None

    src = db.query(schema.Hub).filter(
        schema.Hub.hub_id == msg.source_hub_id
    ).first() if msg.source_hub_id else None

    tgt = db.query(schema.Hub).filter(
        schema.Hub.hub_id == msg.target_hub_id
    ).first() if msg.target_hub_id else None

    return {
        "id": msg.id,
        "category_id": msg.category_id,
        "category_name": cat.category_name if cat else None,
        "source_hub_id": msg.source_hub_id,
        "source_hub_name": src.hub_name if src else None,
        "target_hub_id": msg.target_hub_id,
        "target_hub_name": tgt.hub_name if tgt else "Broadcast",
        "subject": msg.subject,
        "content": msg.content,
        "priority": msg.priority,
        "status": msg.status,
        "sent_at": msg.sent_at,
        "received_at": msg.received_at,
        "published_at": msg.published_at,
        "location": msg.location,
        "created_by": msg.created_by,
        "hop_count": msg.hop_count,
        "ttl": msg.ttl,
        "received_via": msg.received_via,
        "details": msg.details,
    }


# ─── Messages CRUD ───────────────────────────────────────────────────────────

@router.get("/messages")
def list_messages(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(schema.HubMessage).order_by(schema.HubMessage.sent_at.desc())
    if status:
        q = q.filter(schema.HubMessage.status == status)
    if priority:
        q = q.filter(schema.HubMessage.priority == priority)
    messages = q.limit(200).all()
    return {"messages": [_msg_to_response(m, db) for m in messages]}


@router.get("/messages/categories")
def list_categories(db: Session = Depends(get_db)):
    cats = db.query(schema.Category).order_by(schema.Category.category_name).all()
    return {"categories": [CategoryResponse.model_validate(c).model_dump() for c in cats]}


@router.get("/messages/hubs")
def list_hubs(db: Session = Depends(get_db)):
    hubs = db.query(schema.Hub).order_by(schema.Hub.hub_name).all()
    return {"hubs": [HubResponse.model_validate(h).model_dump() for h in hubs]}


@router.get("/messages/{message_id}")
def get_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(schema.HubMessage).filter(schema.HubMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return _msg_to_response(msg, db)


@router.post("/messages")
def create_message(payload: MessageCreate, db: Session = Depends(get_db)):
    now = int(time.time())

    # Use the first hub as the source (this hub)
    this_hub = db.query(schema.Hub).first()
    source_hub_id = this_hub.hub_id if this_hub else None

    msg = schema.HubMessage(
        category_id=payload.category_id,
        source_hub_id=source_hub_id,
        target_hub_id=payload.target_hub_id,
        subject=payload.subject,
        content=payload.content,
        priority=payload.priority,
        status="pending",
        sent_at=now,
        received_via="manual",
        created_by="admin",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    log_change(db, "hub_message", msg.id, "upsert", _msg_to_response(msg, db))
    db.commit()
    
    return _msg_to_response(msg, db)


@router.put("/messages/{message_id}")
def update_message(message_id: int, payload: MessageUpdate, db: Session = Depends(get_db)):
    msg = db.query(schema.HubMessage).filter(schema.HubMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    if payload.status:
        msg.status = payload.status
        if payload.status == "read" and not msg.received_at:
            msg.received_at = int(time.time())
        if payload.status == "published" and not msg.published_at:
            msg.published_at = int(time.time())

    db.commit()
    db.refresh(msg)
    
    log_change(db, "hub_message", msg.id, "upsert", _msg_to_response(msg, db))
    db.commit()
    
    return _msg_to_response(msg, db)


@router.delete("/messages/{message_id}")
def delete_message(message_id: int, db: Session = Depends(get_db)):
    msg = db.query(schema.HubMessage).filter(schema.HubMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    log_change(db, "hub_message", msg.id, "delete", {"id": message_id})
    db.commit()
    return {"status": "deleted"}
