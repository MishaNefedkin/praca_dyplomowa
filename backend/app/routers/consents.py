from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db

router = APIRouter(prefix="/consents", tags=["consents"], dependencies=[Depends(require_roles("admin", "manager"))])


@router.get("/client/{client_id}", response_model=list[schemas.ConsentRead])
def client_consents(client_id: int, db: Annotated[Session, Depends(get_db)]) -> list[models.Consent]:
    return db.query(models.Consent).filter(models.Consent.client_id == client_id).order_by(models.Consent.granted_at.desc()).all()
