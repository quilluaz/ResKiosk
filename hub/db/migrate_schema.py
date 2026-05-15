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
            # Goal 6 / Story 6 — clarification lifecycle logging
            "clarification_triggered": "ALTER TABLE query_logs ADD COLUMN clarification_triggered INTEGER",
            "clarification_trigger_reason": "ALTER TABLE query_logs ADD COLUMN clarification_trigger_reason TEXT",
            "clarification_options_shown": "ALTER TABLE query_logs ADD COLUMN clarification_options_shown TEXT",
            "pipeline_stage_log": "ALTER TABLE query_logs ADD COLUMN pipeline_stage_log TEXT",
            # Slice 6A Story 1: structured query log schema additions
            # Clarification options/selection columns are intentionally omitted —
            # Sprint 2's `clarification_options_shown` and ClarificationResolution
            # already cover those concerns.
            "intent_label": "ALTER TABLE query_logs ADD COLUMN intent_label TEXT",
            "intent_confidence": "ALTER TABLE query_logs ADD COLUMN intent_confidence REAL",
            "lexical_top_k_ids": "ALTER TABLE query_logs ADD COLUMN lexical_top_k_ids TEXT",
            "lexical_top_k_scores": "ALTER TABLE query_logs ADD COLUMN lexical_top_k_scores TEXT",
            "lexical_top_k_ranks": "ALTER TABLE query_logs ADD COLUMN lexical_top_k_ranks TEXT",
            "lexical_latency_ms": "ALTER TABLE query_logs ADD COLUMN lexical_latency_ms REAL",
            "vector_top_k_ids": "ALTER TABLE query_logs ADD COLUMN vector_top_k_ids TEXT",
            "vector_top_k_scores": "ALTER TABLE query_logs ADD COLUMN vector_top_k_scores TEXT",
            "vector_top_k_ranks": "ALTER TABLE query_logs ADD COLUMN vector_top_k_ranks TEXT",
            "fusion_strategy": "ALTER TABLE query_logs ADD COLUMN fusion_strategy TEXT",
            "fusion_top_k_ids": "ALTER TABLE query_logs ADD COLUMN fusion_top_k_ids TEXT",
            "fusion_top_k_scores": "ALTER TABLE query_logs ADD COLUMN fusion_top_k_scores TEXT",
            "fusion_top_k_ranks": "ALTER TABLE query_logs ADD COLUMN fusion_top_k_ranks TEXT",
            "fallback_reason": "ALTER TABLE query_logs ADD COLUMN fallback_reason TEXT",
            "failed_stage": "ALTER TABLE query_logs ADD COLUMN failed_stage TEXT",
            # Goal 9 / Story 7 — feedback-adjusted ranking layer logging
            "bias_enabled": "ALTER TABLE query_logs ADD COLUMN bias_enabled INTEGER",
            "bias_applied_count": "ALTER TABLE query_logs ADD COLUMN bias_applied_count INTEGER",
            "bias_top1_changed": "ALTER TABLE query_logs ADD COLUMN bias_top1_changed INTEGER",
            "bias_detail": "ALTER TABLE query_logs ADD COLUMN bias_detail TEXT",
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
    if cols:
        kb_migrations = {
            "status": "ALTER TABLE kb_articles ADD COLUMN status VARCHAR",
            # Goal 7 (Story 2) filterable metadata
            "authority": "ALTER TABLE kb_articles ADD COLUMN authority TEXT",
            "scope": "ALTER TABLE kb_articles ADD COLUMN scope TEXT",
            "center_id": "ALTER TABLE kb_articles ADD COLUMN center_id TEXT",
            "hub_id": "ALTER TABLE kb_articles ADD COLUMN hub_id TEXT",
        }
        for col, sql in kb_migrations.items():
            if col not in cols:
                cursor.execute(sql)
                print(f"[Migration] Added kb_articles.{col}")
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

    # ── clarification_resolutions ─────────────────────────────────────
    cols = _get_existing_columns(cursor, "clarification_resolutions")
    if cols:
        cr_migrations = {
            # Story 5 (Slice 2): persist full chip selection so resolutions are
            # joinable to query_logs and readable without a taxonomy lookup.
            "selected_option_id":    "ALTER TABLE clarification_resolutions ADD COLUMN selected_option_id TEXT",
            "selected_option_label": "ALTER TABLE clarification_resolutions ADD COLUMN selected_option_label TEXT",
            "query_log_id":          "ALTER TABLE clarification_resolutions ADD COLUMN query_log_id INTEGER",
        }
        for col, sql in cr_migrations.items():
            if col not in cols:
                cursor.execute(sql)
                print(f"[Migration] Added clarification_resolutions.{col}")
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

    # ── Goal 8 / Slice 3 Story 2 — metadata validation storage (new tables) ──
    # New tables use CREATE TABLE IF NOT EXISTS so they are idempotent on any
    # existing DB without needing column introspection.

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_publish_attempts (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_version        INTEGER NOT NULL,
            status            TEXT NOT NULL,
            total_items       INTEGER,
            approved_count    INTEGER,
            quarantined_count INTEGER,
            rejected_count    INTEGER,
            attempted_by      TEXT,
            attempted_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_item_validation_status (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_item_id         INTEGER NOT NULL,
            publish_attempt_id INTEGER,
            kb_version         INTEGER NOT NULL,
            status             TEXT NOT NULL,
            created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_kivs_item ON kb_item_validation_status(kb_item_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_kivs_attempt ON kb_item_validation_status(publish_attempt_id)"
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_validation_results (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_item_id         INTEGER NOT NULL,
            publish_attempt_id INTEGER,
            kb_version         INTEGER NOT NULL,
            rule_id            TEXT NOT NULL,
            severity           TEXT NOT NULL,
            message            TEXT,
            passed             INTEGER NOT NULL,
            checked_at         DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_kvr_item ON kb_validation_results(kb_item_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_kvr_attempt ON kb_validation_results(publish_attempt_id)"
    )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kb_review_decisions (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            kb_item_id         INTEGER NOT NULL,
            publish_attempt_id INTEGER,
            kb_version         INTEGER NOT NULL,
            reviewer_id        TEXT NOT NULL,
            decision           TEXT NOT NULL,
            reason_code        TEXT,
            notes              TEXT,
            decided_at         DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_krd_item ON kb_review_decisions(kb_item_id)"
    )

    conn.commit()
    conn.close()

    if migrated:
        print(f"[Migration] {migrated} column(s) added.")
    else:
        print("[Migration] Schema up to date.")
