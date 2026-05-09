from hub.db.session import SessionLocal
from hub.db import schema

def fix_config():
    db = SessionLocal()
    try:
        cfg = db.query(schema.NetworkConfig).first()
        if cfg:
            print(f"Old config: {cfg.ip_override}:{cfg.port}")
            cfg.ip_override = None
            cfg.port = 8000
            db.commit()
            print("Successfully updated NetworkConfig to port 8000 and auto-IP")
        else:
            print("No NetworkConfig found, creating default...")
            new_cfg = schema.NetworkConfig(ip_override=None, port=8000, network_mode='router')
            db.add(new_cfg)
            db.commit()
            print("Created default NetworkConfig")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_config()
