from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("", response_model=list[schemas.OfferRead], dependencies=[Depends(require_roles("admin", "sales", "manager"))])
def list_offers(
    db: Annotated[Session, Depends(get_db)],
    status: schemas.OfferStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[models.Offer]:
    query = db.query(models.Offer)
    if status:
        query = query.filter(models.Offer.status == status)
    return query.order_by(models.Offer.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=schemas.OfferRead, dependencies=[Depends(require_roles("admin", "sales"))])
def create_offer(payload: schemas.OfferCreate, db: Annotated[Session, Depends(get_db)]) -> models.Offer:
    inquiry = db.get(models.Inquiry, payload.inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    offer = models.Offer(**payload.model_dump())
    if payload.status == "sent":
        inquiry.status = "offer_sent"
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.put("/{offer_id}", response_model=schemas.OfferRead, dependencies=[Depends(require_roles("admin", "sales"))])
def update_offer(offer_id: int, payload: schemas.OfferUpdate, db: Annotated[Session, Depends(get_db)]) -> models.Offer:
    offer = db.get(models.Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(offer, key, value)
    if offer.status == "sent":
        offer.inquiry.status = "offer_sent"
    db.commit()
    db.refresh(offer)
    return offer
