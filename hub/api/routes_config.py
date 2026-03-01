from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.core.auth import get_current_admin
from pydantic import BaseModel
import time

router = APIRouter()

class NetworkConfigUpdate(BaseModel):
    network_mode: str  # 'router' | 'hotspot'
    ip_override: str | None = None
    port: int

@router.get("/network/config")
def get_network_config(db: Session = Depends(get_db)):
    config = db.query(schema.NetworkConfig).first()
    if not config:
        # Default fallback
        return {
            "network_mode": "router",
            "ip_override": "",
            "port": 8000
        }
    return {
        "network_mode": config.network_mode,
        "ip_override": config.ip_override or "",
        "port": config.port or 8000
    }

@router.put("/network/config")
def update_network_config(
    body: NetworkConfigUpdate,
    db: Session = Depends(get_db),
    user: schema.User = Depends(get_current_admin)
):
    # Validation
    if body.network_mode not in ["router", "hotspot"]:
        raise HTTPException(status_code=400, detail="Invalid network mode")
    
    if body.port < 1 or body.port > 65535:
        raise HTTPException(status_code=400, detail="Invalid port number")

    config = db.query(schema.NetworkConfig).first()
    if not config:
        config = schema.NetworkConfig(
            network_mode=body.network_mode,
            ip_override=body.ip_override,
            port=body.port,
            last_updated=int(time.time())
        )
        db.add(config)
    else:
        config.network_mode = body.network_mode
        config.ip_override = body.ip_override
        config.port = body.port
        config.last_updated = int(time.time())
    
    db.commit()
    return {"status": "ok"}
