from sqlalchemy import inspect, text

from hub.db.session import Base, SessionLocal, engine


_MIGRATIONS = [
    ("hub",  "device_id",      "TEXT"),
    ("user", "username",       "TEXT"),
    ("user", "is_first_login", "INTEGER NOT NULL DEFAULT 1"),
    ("user", "created_at",     "INTEGER"),
    ("kb_articles", "created_by", "TEXT DEFAULT 'System Generated'"),
    ("kb_articles", "updated_by", "TEXT"),
    # Goal 7 taxonomy observability (query logs)
    ("query_logs", "ui_selection_source", "TEXT"),
    ("query_logs", "ui_selected_taxonomy_node_id", "TEXT"),
    ("query_logs", "ui_selected_taxonomy_node_label", "TEXT"),
    ("query_logs", "inferred_taxonomy_node_ids", "TEXT"),
    ("query_logs", "widening_step", "TEXT"),
    ("query_logs", "widening_reason", "TEXT"),
]


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
    from hub.db import schema  # noqa: F401 - registers all models with Base
    from hub.db.migrate_schema import migrate
    from hub.db.seed import seed_data

    print("Initializing database...")
    migrate()
    Base.metadata.create_all(bind=engine)
    _migrate_columns()

    db = SessionLocal()
    try:
        seed_data(db)
    finally:
        db.close()

    print("Database initialized.")

