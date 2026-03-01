from sqlalchemy import inspect, text
from hub.db.session import engine, Base, SessionLocal


_MIGRATIONS = [
    ("hub", "device_id", "TEXT"),
    ("user", "email", "TEXT"),
    ("user", "password_hash", "TEXT"),
    ("user", "is_active", "INTEGER DEFAULT 1"),
    ("user", "role", "TEXT DEFAULT 'admin'"),
    ("user", "hub_id", "INTEGER"),
    ("user", "created_at", "INTEGER"),
    ("user", "updated_at", "INTEGER"),
    ("user", "last_login_at", "INTEGER"),
    ("emergency_alerts", "acknowledged_by", "TEXT"),
    ("emergency_alerts", "responding_by", "TEXT"),
]

# Table structures for the new federation system
FEDERATION_TABLES = {
    "hub_peers": [
        ("peer_hub_id", "TEXT PRIMARY KEY"),
        ("peer_name", "TEXT"),
        ("base_url", "TEXT"),
        ("status", "TEXT DEFAULT 'offline'"),
        ("last_seen", "INTEGER"),
        ("last_sync_at", "INTEGER"),
        ("auth_shared_key", "TEXT"),
    ],
    "federation_cursor": [
        ("peer_hub_id", "TEXT PRIMARY KEY"),
        ("last_change_id", "INTEGER DEFAULT 0"),
        ("last_synced_ts", "INTEGER"),
    ],
    "change_log": [
        ("id", "INTEGER PRIMARY KEY AUTOINCREMENT"),
        ("entity_type", "TEXT NOT NULL"),
        ("entity_key", "TEXT NOT NULL"),
        ("op", "TEXT NOT NULL"),
        ("payload_json", "TEXT"),
        ("source_hub_id", "TEXT"),
        ("changed_at", "INTEGER"),
    ],
}


def _migrate_columns():
    """Add any columns that exist in the schema but are missing from the DB."""
    insp = inspect(engine)
    for table, column, col_type in _MIGRATIONS:
        if not insp.has_table(table):
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        if column not in existing:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            print(f"Migrated: added {table}.{column} ({col_type})")


def init_db():
    """Create all tables and seed default rows (safe to call on every startup)."""
    from hub.db import schema  # noqa: F401 — registers all models with Base
    from hub.db.seed import seed_data

    print("Initializing database...")
    Base.metadata.create_all(bind=engine)
    _migrate_columns()

    # Ensure federation tables exist
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.begin() as conn:
        for table_name, columns in FEDERATION_TABLES.items():
            if table_name not in existing_tables:
                col_defs = ", ".join([f"{name} {dtype}" for name, dtype in columns])
                conn.execute(text(f"CREATE TABLE {table_name} ({col_defs})"))
                print(f"Created federation table: {table_name}")

    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

    print("Database initialization complete.")
