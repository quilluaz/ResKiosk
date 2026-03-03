from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from hub.db.session import get_db
from hub.db import schema
from hub.models import api_models

router = APIRouter()


@router.get("/kb/version", response_model=api_models.KBVersionResponse)
async def get_kb_version(db: Session = Depends(get_db)):
    sv = db.query(schema.SystemVersion).first()
    if not sv:
        raise HTTPException(status_code=500, detail="SystemVersion record missing")
    return {"kb_version": sv.kb_version, "updated_at": sv.last_published}


@router.get("/kb/snapshot", response_model=api_models.KBSnapshot)
async def get_kb_snapshot(db: Session = Depends(get_db)):
    sv = db.query(schema.SystemVersion).first()
    articles = db.query(schema.KBArticle).filter(schema.KBArticle.enabled == 1).all()
    evac = db.query(schema.EvacInfo).filter(schema.EvacInfo.id == 1).first()

    # If no evac record exists, create a dummy one for the response
    if not evac:
        evac = schema.EvacInfo(id=1)

    return api_models.KBSnapshot(
        kb_version=sv.kb_version if sv else 0,
        articles=articles,
        structured_config=evac,
    )
