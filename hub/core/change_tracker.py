import json
import time
from sqlalchemy.orm import Session
from hub.db import schema

def log_change(db: Session, entity_type: str, entity_key: str, op: str, payload: dict):
    """
    Records a local mutation in the change_log table so it can be synced by peers.
    """
    try:
        # Get local hub_id
        hub = db.query(schema.Hub).first()
        source_id = str(hub.hub_id) if hub else "unknown"

        change = schema.ChangeLog(
            entity_type=entity_type,
            entity_key=str(entity_key),
            op=op,
            payload_json=json.dumps(payload),
            source_hub_id=source_id,
            changed_at=int(time.time())
        )
        db.add(change)
        # Note: We don't commit here; let the route handler commit the transaction
    except Exception as e:
        print(f"[ChangeTracker] Failed to log change: {e}")
