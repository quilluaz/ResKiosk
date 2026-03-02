import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models
from hub.retrieval.embedder import load_embedder, serialize_embedding, get_embeddable_text
from hub.retrieval.search import invalidate_corpus_cache, invalidate_shelter_config_cache

router = APIRouter()
logger = logging.getLogger(__name__)

FRESHNESS_DAYS = 7
FRESHNESS_SECTIONS = [
    "food_schedule",
    "sleeping_zones",
    "medical_station",
    "registration_steps",
    "announcements",
    "emergency_mode",
]


def _increment_kb_version(db: Session):
    """Bump the kb_version in system_version and record last_published."""
    sv = db.query(schema.SystemVersion).first()
    if sv:
        sv.kb_version = (sv.kb_version or 0) + 1
        sv.last_published = int(time.time())
        db.add(sv)
        db.commit()


def _safe_json_dict(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _get_actor(x_admin_user: str | None) -> str:
    actor = (x_admin_user or "").strip()
    return actor if actor else "system"


def _read_evac_metadata(row: schema.EvacInfo) -> dict:
    return _safe_json_dict(getattr(row, "info_metadata", None))


def _write_evac_metadata(row: schema.EvacInfo, metadata: dict):
    row.info_metadata = json.dumps(metadata, ensure_ascii=True)


def _apply_freshness_stamp(
    row: schema.EvacInfo,
    sections: list[str],
    actor: str,
    now_ts: int,
):
    if not sections:
        return
    metadata = _read_evac_metadata(row)
    freshness = metadata.get("freshness")
    if not isinstance(freshness, dict):
        freshness = {}
    for section in sections:
        freshness[section] = {
            "reviewed_at": now_ts,
            "reviewed_by": actor,
        }
    metadata["freshness"] = freshness
    _write_evac_metadata(row, metadata)


def _fallback_reviewed_at(row: schema.EvacInfo) -> int | None:
    raw = getattr(row, "last_updated", None)
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    try:
        return int(raw)
    except Exception:
        pass
    try:
        return int(time.mktime(time.strptime(raw[:19], "%Y-%m-%dT%H:%M:%S")))
    except Exception:
        return None


def _build_freshness_payload(row: schema.EvacInfo, now_ts: int | None = None) -> dict:
    now = now_ts or int(time.time())
    metadata = _read_evac_metadata(row)
    freshness = metadata.get("freshness")
    if not isinstance(freshness, dict):
        freshness = {}
    fallback_reviewed_at = _fallback_reviewed_at(row)
    sections_payload = []
    expired_sections = []
    ttl_secs = FRESHNESS_DAYS * 24 * 60 * 60
    for section in FRESHNESS_SECTIONS:
        entry = freshness.get(section)
        reviewed_at = None
        reviewed_by = None
        if isinstance(entry, dict):
            reviewed_at = entry.get("reviewed_at")
            reviewed_by = entry.get("reviewed_by")
        if reviewed_at is None:
            reviewed_at = fallback_reviewed_at
        age_days = None
        expires_at = None
        is_expired = True
        if isinstance(reviewed_at, (int, float)):
            reviewed_at = int(reviewed_at)
            age_days = max(0, int((now - reviewed_at) // (24 * 60 * 60)))
            expires_at = reviewed_at + ttl_secs
            is_expired = now >= expires_at
        if is_expired:
            expired_sections.append(section)
        sections_payload.append(
            {
                "section": section,
                "last_reviewed_at": reviewed_at,
                "reviewed_by": reviewed_by,
                "age_days": age_days,
                "expires_at": expires_at,
                "is_expired": is_expired,
            }
        )
    return {
        "freshness_days": FRESHNESS_DAYS,
        "sections": sections_payload,
        "expired_sections": expired_sections,
    }


def _embed_article(db: Session, article: schema.KBArticle):
    """Generate and store embedding for an article."""
    try:
        embedder = load_embedder()
        text = get_embeddable_text(article)
        vec = embedder.embed_text(text)
        article.embedding = serialize_embedding(vec)
        db.add(article)
        db.commit()
        invalidate_corpus_cache()
        print(f"[Embedder] Article {article.id} embedded: '{text[:80]}'")
    except Exception as e:
        print(f"[Embedder] WARNING: Failed to embed article {article.id}: {e}")


# ─── KB Articles ────────────────────────────────────────────────────────────

@router.post("/admin/article", response_model=api_models.ArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article: api_models.ArticleCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_article = schema.KBArticle(
        question=article.question,
        answer=article.answer,
        category=article.category,
        tags=",".join(article.tags) if article.tags else "",
        enabled=1 if article.enabled else 0,
        status=article.status or "draft",
        source="manual",
        created_at=int(time.time()),
        last_updated=int(time.time()),
    )
    db.add(db_article)
    _increment_kb_version(db)
    db.commit()
    db.refresh(db_article)

    background_tasks.add_task(_embed_article, db, db_article)
    return db_article


@router.put("/admin/article/{id}", response_model=api_models.ArticleResponse)
async def update_article(
    id: int,
    update: api_models.ArticleUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    db_article = db.query(schema.KBArticle).filter(schema.KBArticle.id == id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    if db_article.source == "evac_sync":
        raise HTTPException(status_code=403, detail="This article is managed by Shelter Config and cannot be edited here.")

    content_changed = False
    if update.question is not None:
        db_article.question = update.question
        content_changed = True
    if update.answer is not None:
        db_article.answer = update.answer
        content_changed = True
    if update.category is not None:
        db_article.category = update.category
    if update.tags is not None:
        db_article.tags = ",".join(update.tags)
    if update.enabled is not None:
        db_article.enabled = 1 if update.enabled else 0
    if update.status is not None:
        db_article.status = update.status

    db_article.last_updated = int(time.time())
    _increment_kb_version(db)
    db.commit()
    db.refresh(db_article)

    if content_changed:
        background_tasks.add_task(_embed_article, db, db_article)

    return db_article


@router.delete("/admin/article/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(id: int, db: Session = Depends(get_db)):
    db_article = db.query(schema.KBArticle).filter(schema.KBArticle.id == id).first()
    if not db_article:
        raise HTTPException(status_code=404, detail="Article not found")
    if db_article.source == "evac_sync":
        raise HTTPException(status_code=403, detail="This article is managed by Shelter Config and cannot be deleted.")
    db.delete(db_article)
    _increment_kb_version(db)
    db.commit()
    invalidate_corpus_cache()
    invalidate_shelter_config_cache()


# ─── Evac Info (Shelter Operations Config) ──────────────────────────────────

@router.get("/admin/evac", response_model=api_models.EvacInfoResponse)
async def get_evac_info(db: Session = Depends(get_db)):
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not row:
        raise HTTPException(status_code=404, detail="Evac info not found")
    return row


@router.put("/admin/evac", response_model=api_models.EvacInfoUpdateResponse)
async def update_evac_info(
    update: dict,
    x_admin_user: str | None = Header(default=None, alias="X-Admin-User"),
    db: Session = Depends(get_db),
):
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not row:
        row = schema.EvacInfo(id=1)
        db.add(row)

    actor = _get_actor(x_admin_user)
    allowed = FRESHNESS_SECTIONS
    changed_sections = []
    now_ts = int(time.time())
    for field in allowed:
        if field in update:
            incoming = update[field]
            if getattr(row, field, None) != incoming:
                changed_sections.append(field)
            setattr(row, field, incoming)

    # Map 'metadata' from request to 'info_metadata' column
    if "metadata" in update:
        row.info_metadata = update["metadata"]
    _apply_freshness_stamp(row, changed_sections, actor, now_ts)
    row.last_updated = str(now_ts)

    db.commit()
    db.refresh(row)

    # Sync evac fields -> KB articles for semantic search
    from hub.db.evac_sync import sync_evac_to_kb
    sync_result = sync_evac_to_kb(db) or {}
    if sync_result.get("had_any_kb_change"):
        _increment_kb_version(db)
        logger.info("[Freshness] Shelter config auto-published by %s", actor)
    sv = db.query(schema.SystemVersion).first()
    invalidate_corpus_cache()
    invalidate_shelter_config_cache()

    return api_models.EvacInfoUpdateResponse(
        id=row.id,
        food_schedule=row.food_schedule,
        sleeping_zones=row.sleeping_zones,
        medical_station=row.medical_station,
        registration_steps=row.registration_steps,
        announcements=row.announcements,
        emergency_mode=row.emergency_mode,
        last_updated=row.last_updated,
        metadata=row.info_metadata,
        kb_version=sv.kb_version if sv else None,
        published_at=sv.last_published if sv and sync_result.get("had_any_kb_change") else None,
        evac_sync=api_models.EvacSyncSummary(
            changed_count=sync_result.get("changed_count", 0),
            changed_ids=sync_result.get("changed_ids", []),
            disabled_count=sync_result.get("disabled_count", 0),
            embedded_count=sync_result.get("embedded_count", 0),
        ),
    )


@router.get("/admin/evac/freshness", response_model=api_models.EvacFreshnessResponse)
async def get_evac_freshness(db: Session = Depends(get_db)):
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not row:
        row = schema.EvacInfo(id=1)
        db.add(row)
        db.commit()
        db.refresh(row)
    payload = _build_freshness_payload(row)
    return api_models.EvacFreshnessResponse(**payload)


@router.post("/admin/evac/freshness/confirm", response_model=api_models.EvacFreshnessResponse)
async def confirm_evac_freshness(
    payload: api_models.EvacFreshnessConfirmRequest,
    x_admin_user: str | None = Header(default=None, alias="X-Admin-User"),
    db: Session = Depends(get_db),
):
    row = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()
    if not row:
        row = schema.EvacInfo(id=1)
        db.add(row)
    sections = [s for s in (payload.sections or []) if s in FRESHNESS_SECTIONS]
    if not sections:
        raise HTTPException(status_code=400, detail="No valid sections were provided.")
    now_ts = int(time.time())
    actor = _get_actor(x_admin_user)
    _apply_freshness_stamp(row, sections, actor, now_ts)
    row.last_updated = row.last_updated or str(now_ts)
    db.commit()
    db.refresh(row)
    logger.info("[Freshness] Confirmed sections=%s by=%s at=%s", ",".join(sections), actor, now_ts)
    return api_models.EvacFreshnessResponse(**_build_freshness_payload(row, now_ts=now_ts))

# --- Publish (re-embed all) ──────────────────────────────────────────────────

# ─── Publish (re-embed all) ──────────────────────────────────────────────────

@router.post("/admin/publish")
async def publish_kb(db: Session = Depends(get_db)):
    """Re-generate embeddings for all enabled articles and bump KB version."""
    print("[Publish] Regenerating all embeddings...")
    embedder = load_embedder()

    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == 1).all()
    count = 0
    errors = 0
    for art in articles:
        try:
            text = get_embeddable_text(art)
            vec = embedder.embed_text(text)
            art.embedding = serialize_embedding(vec)
            count += 1
        except Exception as e:
            print(f"[Publish] Failed to embed article {art.id}: {e}")
            errors += 1

    _increment_kb_version(db)
    db.commit()
    invalidate_corpus_cache()

    print(f"[Publish] Done. {count} embedded, {errors} errors.")
    return {"status": "published", "articles_processed": count, "errors": errors}


# ─── Bulk Import ─────────────────────────────────────────────────────────────

@router.post("/admin/import")
async def import_articles(payload: dict, db: Session = Depends(get_db)):
    """Bulk import articles. Expects: { "articles": [{question, answer, category, tags, enabled}, ...] }"""
    articles_data = payload.get("articles", [])
    if not isinstance(articles_data, list) or len(articles_data) == 0:
        raise HTTPException(status_code=400, detail="Expected a non-empty 'articles' array.")

    embedder = None
    try:
        embedder = load_embedder()
    except Exception as e:
        print(f"[Import] Warning: Could not load embedder: {e}")

    imported = 0
    skipped = 0
    errors_list = []
    now = int(time.time())

    for i, data in enumerate(articles_data):
        try:
            question = (data.get("question") or "").strip()
            answer = (data.get("answer") or "").strip()
            if not question or not answer:
                skipped += 1
                errors_list.append(f"Item {i+1}: missing question or answer — skipped")
                continue

            article = schema.KBArticle(
                question=question,
                answer=answer,
                category=data.get("category", "General"),
                tags=",".join(data.get("tags", [])) if isinstance(data.get("tags"), list) else (data.get("tags") or ""),
                enabled=1 if data.get("enabled", True) else 0,
                status=data.get("status") or "draft",
                source=data.get("source", "import"),
                created_at=now,
                last_updated=now,
            )

            if embedder:
                try:
                    text = get_embeddable_text(article)
                    vec = embedder.embed_text(text)
                    article.embedding = serialize_embedding(vec)
                except Exception as e:
                    print(f"[Import] Warning: embedding failed for '{question[:50]}': {e}")

            db.add(article)
            imported += 1
        except Exception as e:
            errors_list.append(f"Item {i+1} ('{data.get('question', '?')}'): {e}")

    if imported > 0:
        _increment_kb_version(db)
        db.commit()
        invalidate_corpus_cache()

    print(f"[Import] Done. {imported} imported, {skipped} skipped, {len(errors_list)} errors.")
    return {
        "status": "ok",
        "imported": imported,
        "skipped": skipped,
        "errors": errors_list,
        "total_in_payload": len(articles_data),
    }


# ─── FAQ Tracker ─────────────────────────────────────────────────────────────

@router.get("/admin/faq-tracker", response_model=list[api_models.FAQTrackerItem])
async def get_faq_tracker(limit: int = 200, db: Session = Depends(get_db)):
    """Return FAQ entries sorted by frequency (most asked first)."""
    rows = (
        db.query(schema.FAQTracker)
        .order_by(schema.FAQTracker.count.desc())
        .limit(limit)
        .all()
    )
    return rows


@router.delete("/admin/faq-tracker/{faq_id}", status_code=204)
async def delete_faq_entry(faq_id: int, db: Session = Depends(get_db)):
    """Delete a single FAQ tracker entry."""
    entry = db.query(schema.FAQTracker).filter(schema.FAQTracker.id == faq_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="FAQ entry not found")
    db.delete(entry)
    db.commit()


@router.delete("/admin/faq-tracker", status_code=204)
async def clear_faq_tracker(db: Session = Depends(get_db)):
    """Delete all FAQ tracker entries."""
    db.query(schema.FAQTracker).delete()
    db.commit()
