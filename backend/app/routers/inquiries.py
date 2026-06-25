from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..services.crm import create_inquiry_from_contact_form

router = APIRouter(prefix="/inquiries", tags=["inquiries"])


@router.get("", response_model=list[schemas.InquiryRead], dependencies=[Depends(get_current_user)])
def list_inquiries(
    db: Annotated[Session, Depends(get_db)],
    status: schemas.InquiryStatus | None = Query(default=None),
) -> list[models.Inquiry]:
    query = db.query(models.Inquiry)
    if status:
        query = query.filter(models.Inquiry.status == status)
    return query.order_by(models.Inquiry.created_at.desc()).all()


@router.post("", response_model=schemas.InquiryRead)
def create_inquiry(payload: schemas.InquiryCreate, db: Annotated[Session, Depends(get_db)]) -> models.Inquiry:
    return create_inquiry_from_contact_form(db, payload)


@router.post("/admin", response_model=schemas.InquiryRead, dependencies=[Depends(get_current_user)])
def create_inquiry_admin(payload: schemas.InquiryAdminCreate, db: Annotated[Session, Depends(get_db)]) -> models.Inquiry:
    if not db.get(models.Client, payload.client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    inquiry = models.Inquiry(**payload.model_dump())
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    return inquiry


@router.put("/{inquiry_id}", response_model=schemas.InquiryRead, dependencies=[Depends(get_current_user)])
def update_inquiry(
    inquiry_id: int,
    payload: schemas.InquiryUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> models.Inquiry:
    inquiry = db.get(models.Inquiry, inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(inquiry, key, value)
    db.commit()
    db.refresh(inquiry)
    return inquiry
