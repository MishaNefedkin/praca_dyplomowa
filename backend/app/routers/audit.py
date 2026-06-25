from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_roles("admin", "manager"))])


@router.get("/logs", response_model=list[schemas.AuditLogRead])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    action: str | None = Query(default=None, max_length=120),
    entity_type: str | None = Query(default=None, max_length=80),
    actor_login: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[models.AuditLog]:
    query = db.query(models.AuditLog)
    if action:
        query = query.filter(models.AuditLog.action == action)
    if entity_type:
        query = query.filter(models.AuditLog.entity_type == entity_type)
    if actor_login:
        query = query.filter(models.AuditLog.actor_login == actor_login)
    return query.order_by(models.AuditLog.created_at.desc()).offset(offset).limit(limit).all()
