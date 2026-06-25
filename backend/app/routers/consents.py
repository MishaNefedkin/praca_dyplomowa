from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db
from ..services.audit import record_audit_log

router = APIRouter(prefix="/consents", tags=["consents"], dependencies=[Depends(require_roles("admin", "manager"))])


@router.get("/client/{client_id}", response_model=list[schemas.ConsentRead])
def client_consents(client_id: int, db: Annotated[Session, Depends(get_db)]) -> list[models.Consent]:
    return (
        db.query(models.Consent)
        .filter(models.Consent.client_id == client_id)
        .order_by(models.Consent.granted_at.desc())
        .all()
    )


@router.put("/{consent_id}", response_model=schemas.ConsentRead)
def update_consent(
    consent_id: int,
    payload: schemas.ConsentUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "manager"))],
) -> models.Consent:
    consent = db.get(models.Consent, consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail="Consent not found")
    consent.active = payload.active
    record_audit_log(
        db,
        actor,
        action="consent.update",
        entity_type="consent",
        entity_id=consent.id,
        details={"active": consent.active, "client_id": consent.client_id, "scope": consent.scope},
    )
    db.commit()
    db.refresh(consent)
    return consent
