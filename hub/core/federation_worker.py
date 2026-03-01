import threading
import time
import requests
import json
from hub.db.session import SessionLocal
from hub.db import schema
from sqlalchemy.orm import Session

class FederationWorker:
    def __init__(self, interval=30):
        self.interval = interval
        self.running = False
        self._thread = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[FederationWorker] Background sync started (interval: {self.interval}s)")

    def _run_loop(self):
        while self.running:
            try:
                self._sync_all_peers()
            except Exception as e:
                print(f"[FederationWorker] Sync error: {e}")
            time.sleep(self.interval)

    def _sync_all_peers(self):
        db = SessionLocal()
        try:
            peers = db.query(schema.HubPeer).filter(schema.HubPeer.status == "online").all()
            for peer in peers:
                self._sync_peer(db, peer)
        finally:
            db.close()

    def _sync_peer(self, db: Session, peer: schema.HubPeer):
        # Get cursor
        cursor = db.query(schema.FederationCursor).filter(
            schema.FederationCursor.peer_hub_id == peer.peer_hub_id
        ).first()
        
        last_id = cursor.last_change_id if cursor else 0
        
        try:
            url = f"{peer.base_url}/federation/changes?after_id={last_id}"
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"[FederationWorker] Failed to pull from {peer.peer_name}: {response.status_code}")
                return

            data = response.json()
            changes = data.get("changes", [])
            
            if not changes:
                return

            print(f"[FederationWorker] Pulling {len(changes)} changes from {peer.peer_name}...")
            
            for change in changes:
                self._apply_change(db, change)
                last_id = max(last_id, change["id"])

            # Update cursor
            if not cursor:
                cursor = schema.FederationCursor(
                    peer_hub_id=peer.peer_hub_id,
                    last_change_id=last_id,
                    last_synced_ts=int(time.time())
                )
                db.add(cursor)
            else:
                cursor.last_change_id = last_id
                cursor.last_synced_ts = int(time.time())
            
            db.commit()
            peer.last_sync_at = int(time.time())
            db.commit()

        except Exception as e:
            print(f"[FederationWorker] Sync failed for {peer.peer_name}: {e}")

    def _apply_change(self, db: Session, change: dict):
        entity_type = change["entity_type"]
        op = change["op"]
        payload = change["payload"]
        source_hub_id = change["source_hub_id"]

        if entity_type == "emergency_alert":
            self._apply_alert(db, payload, source_hub_id)
        elif entity_type == "kiosk":
            self._apply_kiosk(db, payload, source_hub_id)
        elif entity_type == "hub_message":
            self._apply_message(db, payload, source_hub_id)

    def _apply_alert(self, db: Session, payload: dict, source_id: str):
        # Find if alert exists (id is local to source)
        # For federation, we should probably have a global identifier or use (source_id, local_id)
        # The schema has 'alert_id_local' but many use the primary key 'id'
        # In this simplistic v1, we use payload['id'] as the peer's local ID
        # and we store it in a way that avoids collisions.
        # However, to keep it simple as per PLAN.md "mirroring", we upsert.
        
        # Collision prevention: if it's mirrored, it should store source_hub_id
        # Let's use (hub_id, local_id) logic if possible.
        # Current schema has alert_id_local. Let's use that.
        
        local_id = payload.get("id")
        existing = db.query(schema.EmergencyAlert).filter(
            schema.EmergencyAlert.hub_id == source_id,
            schema.EmergencyAlert.alert_id_local == str(local_id)
        ).first()

        if not existing:
            alert = schema.EmergencyAlert(
                kiosk_id=payload.get("kiosk_id"),
                kiosk_location=payload.get("kiosk_location"),
                hub_id=source_id,
                transcript=payload.get("transcript"),
                language=payload.get("language", "en"),
                timestamp=payload.get("timestamp"),
                status=payload.get("status"),
                tier=payload.get("tier", 1),
                alert_id_local=str(local_id),
                acknowledged_at=payload.get("acknowledged_at"),
                acknowledged_by=payload.get("acknowledged_by"),
                responding_at=payload.get("responding_at"),
                responding_by=payload.get("responding_by"),
                resolution_notes=payload.get("resolution_notes"),
                resolved_by=payload.get("resolved_by"),
                resolved=payload.get("resolved", 0),
                resolved_at=payload.get("resolved_at")
            )
            db.add(alert)
        else:
            # Update
            existing.status = payload.get("status")
            existing.acknowledged_at = payload.get("acknowledged_at")
            existing.acknowledged_by = payload.get("acknowledged_by")
            existing.responding_at = payload.get("responding_at")
            existing.responding_by = payload.get("responding_by")
            existing.resolution_notes = payload.get("resolution_notes")
            existing.resolved_by = payload.get("resolved_by")
            existing.resolved = payload.get("resolved", 0)
            existing.resolved_at = payload.get("resolved_at")

    def _apply_kiosk(self, db: Session, payload: dict, source_id: str):
        kid = payload.get("kiosk_id")
        existing = db.query(schema.Kiosk).filter(
            schema.Kiosk.hub_id == source_id,
            schema.Kiosk.kiosk_name == kid # We use name as the natural key for discovery
        ).first()

        if not existing:
            k = schema.Kiosk(
                hub_id=source_id,
                kiosk_name=kid,
                status=payload.get("status", "online"),
                last_seen=int(time.time()),
                created_at=int(time.time())
            )
            db.add(k)
        else:
            existing.status = payload.get("status", "online")
            existing.last_seen = int(time.time())

    def _apply_message(self, db: Session, payload: dict, source_id: str):
        # Simplistic message mirroring
        mid = payload.get("id")
        # We don't have a source_msg_id in schema, let's skip complex dedup for v1 messages
        # or just check subject/source/content
        pass

federation_worker = FederationWorker()
