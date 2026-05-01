"""
Idempotent schema migration: adds missing columns/tables to existing DBs.
Called by init_db.py BEFORE create_all() to handle cases where a table
exists from an older schema version and is missing newly-added columns.
create_all() cannot ALTER existing tables — it only creates missing ones.
"""
import sqlite3
import os
from pathlib import Path


def _get_db_path():
    db_path = os.environ.get("RESKIOSK_DB_PATH")
    if not db_path:
        if os.name == "nt":
            base = Path(os.environ.get("APPDATA", "")) / "ResKiosk"
        else:
            base = Path.home() / ".local" / "share" / "reskiosk"
        db_path = str(base / "reskiosk.db")
    return db_path


def _get_existing_columns(cursor, table):
    """Return set of column names for a given table, or empty set if table doesn't exist."""
    try:
        cursor.execute(f"PRAGMA table_info({table})")
        return {row[1] for row in cursor.fetchall()}
    except Exception:
        return set()


def migrate():
    """Run idempotent ALTER TABLE migrations for any missing columns."""
    path = _get_db_path()
    if not os.path.exists(path):
        return  # Fresh install — create_all() will handle everything

    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    migrated = 0

    # ── query_logs ────────────────────────────────────────────────────
    cols = _get_existing_columns(cursor, "query_logs")
    if cols:  # Table exists
        ql_migrations = {
            "source_id": "ALTER TABLE query_logs ADD COLUMN source_id INTEGER",
            "rewrite_attempted": "ALTER TABLE query_logs ADD COLUMN rewrite_attempted INTEGER DEFAULT 0",
            "rewritten_query": "ALTER TABLE query_logs ADD COLUMN rewritten_query TEXT",
            "raw_transcript": "ALTER TABLE query_logs ADD COLUMN raw_transcript TEXT",
            "normalized_transcript": "ALTER TABLE query_logs ADD COLUMN normalized_transcript TEXT",
            "session_id": "ALTER TABLE query_logs ADD COLUMN session_id TEXT",
            "rlhf_top_source_id": "ALTER TABLE query_logs ADD COLUMN rlhf_top_source_id INTEGER",
            "rlhf_top_score": "ALTER TABLE query_logs ADD COLUMN rlhf_top_score REAL",
            "retrieval_score": "ALTER TABLE query_logs ADD COLUMN retrieval_score REAL",
            "formatter_mode": "ALTER TABLE query_logs ADD COLUMN formatter_mode TEXT",
            "stt_mode": "ALTER TABLE query_logs ADD COLUMN stt_mode TEXT",
            "tts_mode": "ALTER TABLE query_logs ADD COLUMN tts_mode TEXT",
            "connectivity_state": "ALTER TABLE query_logs ADD COLUMN connectivity_state TEXT",
            "cloud_consent_mode": "ALTER TABLE query_logs ADD COLUMN cloud_consent_mode TEXT DEFAULT 'disabled'",
            # Goal 7 taxonomy observability (additive)
            "ui_selection_source": "ALTER TABLE query_logs ADD COLUMN ui_selection_source TEXT",
            "ui_selected_taxonomy_node_id": "ALTER TABLE query_logs ADD COLUMN ui_selected_taxonomy_node_id TEXT",
            "ui_selected_taxonomy_node_label": "ALTER TABLE query_logs ADD COLUMN ui_selected_taxonomy_node_label TEXT",
            "inferred_taxonomy_node_ids": "ALTER TABLE query_logs ADD COLUMN inferred_taxonomy_node_ids TEXT",
            "widening_step": "ALTER TABLE query_logs ADD COLUMN widening_step TEXT",
            "widening_reason": "ALTER TABLE query_logs ADD COLUMN widening_reason TEXT",
        }
        for col, sql in ql_migrations.items():
            if col not in cols:
                cursor.execute(sql)
                print(f"[Migration] Added query_logs.{col}")
                migrated += 1
        if "cloud_consent_mode" in ql_migrations:
            cursor.execute(
                "UPDATE query_logs SET cloud_consent_mode = 'disabled' "
                "WHERE cloud_consent_mode IS NULL OR cloud_consent_mode = ''"
            )

    # ── kb_articles ───────────────────────────────────────────────────
    cols = _get_existing_columns(cursor, "kb_articles")
    if cols and "status" not in cols:
        cursor.execute("ALTER TABLE kb_articles ADD COLUMN status VARCHAR")
        print("[Migration] Added kb_articles.status")
        migrated += 1

    # -- network_config -------------------------------------------------------
    cols = _get_existing_columns(cursor, "network_config")
    if cols:
        net_migrations = {
            "cloud_enabled": "ALTER TABLE network_config ADD COLUMN cloud_enabled INTEGER DEFAULT 0",
            "cloud_user_overridden": "ALTER TABLE network_config ADD COLUMN cloud_user_overridden INTEGER DEFAULT 0",
            "cloud_last_changed_at": "ALTER TABLE network_config ADD COLUMN cloud_last_changed_at INTEGER",
        }
        for col, sql in net_migrations.items():
            if col not in cols:
                cursor.execute(sql)
                print(f"[Migration] Added network_config.{col}")
                migrated += 1

    # ── emergency_alerts ───────────────────────────────────────────────────────────────
    cols = _get_existing_columns(cursor, "emergency_alerts")
    if cols:
        em_migrations = {
            "status": "ALTER TABLE emergency_alerts ADD COLUMN status TEXT DEFAULT 'ACTIVE'",
            "tier": "ALTER TABLE emergency_alerts ADD COLUMN tier INTEGER DEFAULT 1",
            "alert_id_local": "ALTER TABLE emergency_alerts ADD COLUMN alert_id_local TEXT",
            "acknowledged_at": "ALTER TABLE emergency_alerts ADD COLUMN acknowledged_at INTEGER",
            "responding_at": "ALTER TABLE emergency_alerts ADD COLUMN responding_at INTEGER",
            "dismissed_by_kiosk": "ALTER TABLE emergency_alerts ADD COLUMN dismissed_by_kiosk INTEGER DEFAULT 0",
            "dismissed_at": "ALTER TABLE emergency_alerts ADD COLUMN dismissed_at INTEGER",
            "resolution_notes": "ALTER TABLE emergency_alerts ADD COLUMN resolution_notes TEXT",
            "resolved_by": "ALTER TABLE emergency_alerts ADD COLUMN resolved_by TEXT",
            "retry_count": "ALTER TABLE emergency_alerts ADD COLUMN retry_count INTEGER DEFAULT 0",
        }
        for col, sql in em_migrations.items():
            if col not in cols:
                cursor.execute(sql)
                print(f"[Migration] Added emergency_alerts.{col}")
                migrated += 1
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_local ON emergency_alerts(alert_id_local)")

    # -- evac_info -----------------------------------------------------------
    cols = _get_existing_columns(cursor, "evac_info")
    if cols and "food_distribution_location" not in cols:
        cursor.execute("ALTER TABLE evac_info ADD COLUMN food_distribution_location TEXT")
        print("[Migration] Added evac_info.food_distribution_location")
        migrated += 1

    # ── faq_tracker (new table) ────────────────────────────────────────
    # Drop and recreate if schema changed (safe: FAQ data is transient analytics)
    cursor.execute("DROP TABLE IF EXISTS faq_tracker")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faq_tracker (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id           INTEGER NOT NULL UNIQUE,
            source_question     TEXT,
            source_answer       TEXT,
            question_normalized TEXT,
            question_display    TEXT,
            language            VARCHAR,
            count               INTEGER NOT NULL DEFAULT 1,
            first_asked_at      INTEGER,
            last_asked_at       INTEGER,
            kiosk_id            VARCHAR,
            answer_type         VARCHAR
        )
    """)
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_faq_source ON faq_tracker(source_id)")

    conn.commit()
    conn.close()

    if migrated:
        print(f"[Migration] {migrated} column(s) added.")
    else:
        print("[Migration] Schema up to date.")
