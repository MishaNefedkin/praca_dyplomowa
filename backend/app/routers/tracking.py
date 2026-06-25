from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.post("/event", response_model=schemas.ActivityLogRead)
def track_event(payload: schemas.TrackingEventCreate, db: Annotated[Session, Depends(get_db)]) -> models.ActivityLog:
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
