from typing import Annotated
from time import monotonic

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/tracking", tags=["tracking"])
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_EVENTS = 60
rate_limit_hits: dict[str, list[float]] = {}


def check_rate_limit(request: Request, session_id: str) -> None:
    now = monotonic()
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{session_id}"
    recent_hits = [
        hit for hit in rate_limit_hits.get(key, [])
        if now - hit < RATE_LIMIT_WINDOW_SECONDS
    ]
    if len(recent_hits) >= RATE_LIMIT_MAX_EVENTS:
        rate_limit_hits[key] = recent_hits
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many tracking events")
    recent_hits.append(now)
    rate_limit_hits[key] = recent_hits


@router.post("/event", response_model=schemas.ActivityLogRead)
def track_event(
    payload: schemas.TrackingEventCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> models.ActivityLog:
    check_rate_limit(request, payload.session_id)
    client = db.query(models.Client).filter(models.Client.session_id == payload.session_id).first()
    log = models.ActivityLog(**payload.model_dump(), client_id=client.id if client else None)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("/logs", response_model=list[schemas.ActivityLogRead], dependencies=[Depends(get_current_user)])
def list_logs(
    db: Annotated[Session, Depends(get_db)],
    event_type: str | None = Query(default=None),
    client_id: int | None = Query(default=None),
) -> list[models.ActivityLog]:
    query = db.query(models.ActivityLog)
    if event_type:
        query = query.filter(models.ActivityLog.event_type == event_type)
    if client_id:
        query = query.filter(models.ActivityLog.client_id == client_id)
    return query.order_by(models.ActivityLog.logged_at.desc()).limit(300).all()
