from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from typing import List, Optional
import json

router = APIRouter(prefix="/federation", tags=["federation"])

@router.get("/changes")
def get_changes(
    after_id: int = Query(0),
    limit: int = Query(100),
    db: Session = Depends(get_db)
):
    """
    Returns a list of local mutations that peers can use to sync their state.
    """
    changes = db.query(schema.ChangeLog).filter(
        schema.ChangeLog.id > after_id
    ).order_by(schema.ChangeLog.id.asc()).limit(limit).all()

    results = []
    for c in changes:
        results.append({
            "id": c.id,
            "entity_type": c.entity_type,
            "entity_key": c.entity_key,
            "op": c.op,
            "payload": json.loads(c.payload_json) if c.payload_json else {},
            "source_hub_id": c.source_hub_id,
            "changed_at": c.changed_at
        })
    
    return {"changes": results}

@router.get("/peers")
def get_peers(db: Session = Depends(get_db)):
    """
    Returns a list of discovered peer hubs and their status.
    """
    peers = db.query(schema.HubPeer).all()
    return {
        "peers": [
            {
                "peer_hub_id": p.peer_hub_id,
                "peer_name": p.peer_name,
                "base_url": p.base_url,
                "status": p.status,
                "last_seen": p.last_seen,
                "last_sync_at": p.last_sync_at
            } for p in peers
        ]
    }
