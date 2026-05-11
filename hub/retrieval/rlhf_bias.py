import os
import sys
import time
from collections import defaultdict
from pathlib import Path

from hub.db.session import SessionLocal, engine
from hub.db import schema


MIN_EVENTS = int(os.environ.get("RESKIOSK_RLHF_MIN_EVENTS", 3))
DECAY_FACTOR = float(os.environ.get("RESKIOSK_RLHF_DECAY", 0.9))


def _acquire_lock() -> bool:
    """
    Best-effort file lock to avoid concurrent rebuilds.
    Returns True if lock acquired, False otherwise.
    """
    lock_dir = Path(os.environ.get("RESKIOSK_RLHF_LOCK_DIR", os.getcwd()))
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "rlhf_bias.lock"
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        os.close(fd)
        return True
    except FileExistsError:
        return False


def _release_lock():
    lock_dir = Path(os.environ.get("RESKIOSK_RLHF_LOCK_DIR", os.getcwd()))
    lock_path = lock_dir / "rlhf_bias.lock"
    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass


def rebuild():
    """
    Recompute ArticleBias entries from FeedbackLog using a decayed log-ratio model.
    Safe to run periodically (cron or manual).
    """
    if not _acquire_lock():
        print("[RLHF] Another rebuild is already running; exiting.")
        return

    db = SessionLocal()
    try:
        # Load existing biases and KB article IDs
        existing_biases = {row.source_id: float(row.bias) for row in db.query(schema.ArticleBias).all()}
        kb_ids = {row.id for row in db.query(schema.KBArticle.id).all()}

        # Aggregate lifetime feedback per source_id
        stats = defaultdict(lambda: {"pos": 0, "neg": 0})
        for fb in db.query(schema.FeedbackLog).all():
            if fb.source_id is None:
                continue
            s = stats[fb.source_id]
            if fb.label > 0:
                s["pos"] += 1
            elif fb.label < 0:
                s["neg"] += 1

        # Recompute bias for all source_ids that either have feedback or an existing bias
        all_source_ids = set(existing_biases.keys()) | set(stats.keys())
        now = time.time()

        for source_id in all_source_ids:
            pos = stats[source_id]["pos"]
            neg = stats[source_id]["neg"]
            n = pos + neg

            prev_bias = existing_biases.get(source_id, 0.0)

            if n < MIN_EVENTS:
                # Not enough signal yet: decay toward 0
                combined = DECAY_FACTOR * prev_bias
            else:
                # Fresh log-ratio from lifetime counts
                from math import log

                raw = log((pos + 1.0) / (neg + 1.0))
                decayed_prev = DECAY_FACTOR * prev_bias
                combined = decayed_prev + (1.0 - DECAY_FACTOR) * raw

            # Clamp to [-1, 1]
            bias = max(-1.0, min(1.0, combined))

            # Upsert ArticleBias row
            row = db.query(schema.ArticleBias).filter(schema.ArticleBias.source_id == source_id).first()
            if row is None:
                row = schema.ArticleBias(source_id=source_id, bias=bias)
                db.add(row)
            else:
                row.bias = bias

        # Cleanup: remove biases for articles that no longer exist
        if kb_ids:
            db.query(schema.ArticleBias).filter(~schema.ArticleBias.source_id.in_(kb_ids)).delete(
                synchronize_session=False
            )

        db.commit()
        print("[RLHF] Rebuild complete.")
    except Exception as e:
        db.rollback()
        print(f"[RLHF] Rebuild failed: {e}", file=sys.stderr)
        raise
    finally:
        db.close()
        _release_lock()


if __name__ == "__main__":
    rebuild()

