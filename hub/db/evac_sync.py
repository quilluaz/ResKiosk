"""
Sync EvacInfo fields → KBArticle rows so shelter operations data
is vectorized and searchable via semantic search.

Every non-empty evac_info field becomes one KBArticle with
source='evac_sync'.  Synced articles are upserted (created or updated)
and re-embedded whenever the evac_info row changes.
"""

import time
from sqlalchemy.orm import Session
from hub.db import schema

# Mapping: evac_info field → (question, tags)
FIELD_MAP = {
    "food_schedule": (
        "What is the food schedule?",
        "food,schedule,meals,breakfast,lunch,dinner",
    ),
    "food_distribution_location": (
        "Where is the food and water distribution?",
        "food,water,distribution,location,meal line,nutrition",
    ),
    "sleeping_zones": (
        "Where are the sleeping zones?",
        "sleeping,zones,rest,beds,cots",
    ),
    "medical_station": (
        "Where is the medical station?",
        "medical,station,health,doctor,nurse,first aid",
    ),
    "registration_steps": (
        "How do I register?",
        "registration,steps,sign-up,check-in,intake",
    ),
    "announcements": (
        "What are the current announcements?",
        "announcements,updates,notices",
    ),
}

EVAC_SOURCE = "evac_sync"
EVAC_CATEGORY = "Shelter Operations"


def sync_evac_to_kb(db: Session):
    """Upsert one KBArticle per non-empty EvacInfo field.

    Embedding is done inline (not as a background task) because evac
    fields are short sentences and embedding is nearly instant.  This
    avoids session-lifecycle issues when the console calls PUT /admin/evac
    followed immediately by POST /admin/publish.
    """
    evac = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not evac:
        return {
            "changed_count": 0,
            "changed_ids": [],
            "disabled_count": 0,
            "embedded_count": 0,
            "had_any_kb_change": False,
        }

    # Load existing evac_sync articles keyed by question
    existing = {
        art.question: art
        for art in db.query(schema.KBArticle)
        .filter(schema.KBArticle.source == EVAC_SOURCE)
        .all()
    }

    now = int(time.time())
    changed_articles = []
    disabled_count = 0

    for field, (question, tags) in FIELD_MAP.items():
        value = (getattr(evac, field, None) or "").strip()
        art = existing.get(question)

        if value:
            if art:
                # Update only if the answer actually changed
                if art.answer != value:
                    art.answer = value
                    art.tags = tags
                    art.enabled = 1
                    art.status = "published"
                    art.last_updated = now
                    art.embedding = None  # Will be re-embedded below
                    changed_articles.append(art)
                elif art.status != "published":
                    # Keep Shelter Config synced articles in published state.
                    art.status = "published"
                    art.last_updated = now
                    changed_articles.append(art)
            else:
                # Create new article
                art = schema.KBArticle(
                    question=question,
                    answer=value,
                    category=EVAC_CATEGORY,
                    tags=tags,
                    enabled=1,
                    status="published",
                    source=EVAC_SOURCE,
                    created_at=now,
                    last_updated=now,
                )
                db.add(art)
                changed_articles.append(art)
        else:
            # Field is empty → disable the article if it exists
            if art and art.enabled:
                art.enabled = 0
                art.last_updated = now
                disabled_count += 1

    db.commit()

    if not changed_articles:
        if disabled_count > 0:
            from hub.retrieval.search import invalidate_corpus_cache
            invalidate_corpus_cache()
            print(f"[EvacSync] {disabled_count} article(s) disabled.")
        else:
            print("[EvacSync] No changes detected.")
        return {
            "changed_count": 0,
            "changed_ids": [],
            "disabled_count": disabled_count,
            "embedded_count": 0,
            "had_any_kb_change": disabled_count > 0,
        }

    # Embed changed articles inline (fast — only short sentences)
    from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text
    from hub.retrieval.search import invalidate_corpus_cache

    embedder = load_embedder()
    embedded_count = 0
    for art in changed_articles:
        try:
            db.refresh(art)
            text = get_embeddable_text(art)
            vec = embedder.embed_text(text)
            art.embedding = serialize_embedding(vec)
            embedded_count += 1
            print(f"[EvacSync] Embedded article {art.id}: '{art.question}'")
        except Exception as e:
            print(f"[EvacSync] WARNING: Failed to embed '{art.question}': {e}")

    db.commit()
    invalidate_corpus_cache()
    print(f"[EvacSync] changed={len(changed_articles)} disabled={disabled_count} embedded={embedded_count}")
    return {
        "changed_count": len(changed_articles),
        "changed_ids": [art.id for art in changed_articles if art.id is not None],
        "disabled_count": disabled_count,
        "embedded_count": embedded_count,
        "had_any_kb_change": True,
    }
