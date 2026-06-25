from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db
from ..services.audit import record_audit_log

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


@router.post("", response_model=schemas.OfferRead)
def create_offer(
    payload: schemas.OfferCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "sales"))],
) -> models.Offer:
    inquiry = db.get(models.Inquiry, payload.inquiry_id)
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    offer = models.Offer(**payload.model_dump())
    if payload.status == "sent":
        inquiry.status = "offer_sent"
    db.add(offer)
    db.flush()
    record_audit_log(
        db,
        actor,
        action="offer.create",
        entity_type="offer",
        entity_id=offer.id,
        details={"inquiry_id": offer.inquiry_id, "status": offer.status, "value": offer.value},
    )
    db.commit()
    db.refresh(offer)
    return offer


@router.put("/{offer_id}", response_model=schemas.OfferRead)
def update_offer(
    offer_id: int,
    payload: schemas.OfferUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "sales"))],
) -> models.Offer:
    offer = db.get(models.Offer, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(offer, key, value)
    if offer.status == "sent":
        offer.inquiry.status = "offer_sent"
    record_audit_log(
        db,
        actor,
        action="offer.update",
        entity_type="offer",
        entity_id=offer.id,
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(offer)
    return offer
