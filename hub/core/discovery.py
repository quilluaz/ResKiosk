import os
import socket
import threading
import json
import time
from hub.db.session import SessionLocal
from hub.db import schema
from hub.core.network_manager import network_manager

class DiscoveryService:
    def __init__(self, port=9999):
        self.port = port
        self.running = False
        self._threads = []

    def start(self):
        self.running = True
        t1 = threading.Thread(target=self._broadcast_loop, daemon=True)
        t2 = threading.Thread(target=self._listen_loop, daemon=True)
        t1.start()
        t2.start()
        self._threads = [t1, t2]
        print(f"[Discovery] Service started on UDP {self.port}")

    def _broadcast_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        while self.running:
            try:
                db = SessionLocal()
                # Get local hub identity
                hub = db.query(schema.Hub).first()
                config = db.query(schema.NetworkConfig).first()
                db.close()

                if hub:
                    ip = config.ip_override if (config and config.ip_override) else network_manager.detect_ip()
                    port = config.port if (config and config.port) else int(os.environ.get("HUB_PORT", 8000))
                    
                    payload = {
                        "type": "RESKIOSK_HUB_DISCOVERY",
                        "hub_id": str(hub.hub_id),
                        "hub_name": hub.hub_name,
                        "base_url": f"http://{ip}:{port}"
                    }
                    data = json.dumps(payload).encode("utf-8")
                    sock.sendto(data, ("<broadcast>", self.port))
            except Exception as e:
                print(f"[Discovery] Broadcast error: {e}")
            
            time.sleep(10)

    def _listen_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", self.port))
        except OSError as e:
            print(f"[Discovery] Could not bind listener on UDP {self.port}: {e}")
            print(f"[Discovery] Another hub may already be listening. Broadcasting will still work.")
            return

        while self.running:
            try:
                data, addr = sock.recvfrom(2048)
                payload = json.loads(data.decode("utf-8"))
                
                if payload.get("type") == "RESKIOSK_HUB_DISCOVERY":
                    self._handle_discovered_hub(payload)
            except Exception as e:
                # Silent fail for garbage packets
                pass

    def _handle_discovered_hub(self, payload):
        peer_id = payload["hub_id"]
        peer_name = payload["hub_name"]
        url = payload["base_url"]

        db = SessionLocal()
        try:
            # Don't add ourselves as a peer
            local_hub = db.query(schema.Hub).first()
            if local_hub and str(local_hub.hub_id) == peer_id:
                return

            peer = db.query(schema.HubPeer).filter(schema.HubPeer.peer_hub_id == peer_id).first()
            if not peer:
                peer = schema.HubPeer(
                    peer_hub_id=peer_id,
                    peer_name=peer_name,
                    base_url=url,
                    status="online",
                    last_seen=int(time.time())
                )
                db.add(peer)
                print(f"[Discovery] Found NEW peer: {peer_name} ({peer_id}) at {url}")
            else:
                peer.peer_name = peer_name
                peer.base_url = url
                peer.status = "online"
                peer.last_seen = int(time.time())
            
            db.commit()
        except Exception as e:
            print(f"[Discovery] Failed to update peer: {e}")
        finally:
            db.close()

discovery_service = DiscoveryService()
