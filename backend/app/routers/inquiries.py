from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db
from ..services.audit import record_audit_log
from ..services.crm import create_inquiry_from_contact_form

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.get(
    "", response_model=list[schemas.InquiryRead], dependencies=[Depends(require_roles("admin", "sales", "manager"))]
)
def list_inquiries(
    db: Annotated[Session, Depends(get_db)],
    status: schemas.InquiryStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[models.Inquiry]:
    query = db.query(models.Inquiry)
    if status:
        query = query.filter(models.Inquiry.status == status)
    return query.order_by(models.Inquiry.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=schemas.InquiryRead)
def create_inquiry(payload: schemas.InquiryCreate, db: Annotated[Session, Depends(get_db)]) -> models.Inquiry:
    return create_inquiry_from_contact_form(db, payload)


@router.post("/admin", response_model=schemas.InquiryRead)
def create_inquiry_admin(
    payload: schemas.InquiryAdminCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "sales"))],
) -> models.Inquiry:
    if not db.get(models.Client, payload.client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    inquiry = models.Inquiry(**payload.model_dump())
    db.add(inquiry)
    db.flush()
    record_audit_log(
        db,
        actor,
        action="inquiry.create",
        entity_type="inquiry",
        entity_id=inquiry.id,
        details={"client_id": inquiry.client_id, "status": inquiry.status},
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.get(
    "/{inquiry_id}",
    response_model=schemas.InquiryRead,
    dependencies=[Depends(require_roles("admin", "sales", "manager"))],
)
def get_inquiry(inquiry_id: int, db: Annotated[Session, Depends(get_db)]) -> models.Inquiry:
    inquiry = db.get(models.Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry


@router.put("/{inquiry_id}", response_model=schemas.InquiryRead)
def update_inquiry(
    inquiry_id: int,
    payload: schemas.InquiryUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "sales"))],
) -> models.Inquiry:
    inquiry = db.get(models.Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(inquiry, key, value)
    record_audit_log(
        db,
        actor,
        action="inquiry.update",
        entity_type="inquiry",
        entity_id=inquiry.id,
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.delete("/{inquiry_id}", response_model=schemas.InquiryRead)
def delete_inquiry(
    inquiry_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin"))],
) -> schemas.InquiryRead:
    inquiry = db.get(models.Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    deleted_inquiry = schemas.InquiryRead.model_validate(inquiry)
    record_audit_log(
        db,
        actor,
        action="inquiry.delete",
        entity_type="inquiry",
        entity_id=inquiry.id,
        details={"client_id": inquiry.client_id, "status": inquiry.status},
    )
    db.delete(inquiry)
    db.commit()
    return deleted_inquiry
