from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db
from ..services.audit import record_audit_log

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[schemas.ClientRead], dependencies=[Depends(require_roles("admin", "sales", "manager"))])
def list_clients(
    db: Annotated[Session, Depends(get_db)],
    q: str | None = Query(default=None, min_length=2, max_length=120),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[models.Client]:
    query = db.query(models.Client)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                models.Client.name.ilike(pattern),
                models.Client.email.ilike(pattern),
                models.Client.phone.ilike(pattern),
            )
        )
    return query.order_by(models.Client.created_at.desc()).offset(offset).limit(limit).all()


@router.post("", response_model=schemas.ClientRead)
def create_client(
    payload: schemas.ClientCreate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "sales"))],
) -> models.Client:
    if db.query(models.Client).filter(models.Client.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Client with this email already exists")
    client = models.Client(**payload.model_dump())
    db.add(client)
    db.flush()
    record_audit_log(
        db,
        actor,
        action="client.create",
        entity_type="client",
        entity_id=client.id,
        details={"has_email": client.email is not None},
    )
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=schemas.ClientRead, dependencies=[Depends(require_roles("admin", "sales", "manager"))])
def get_client(client_id: int, db: Annotated[Session, Depends(get_db)]) -> models.Client:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=schemas.ClientRead)
def update_client(
    client_id: int,
    payload: schemas.ClientUpdate,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "sales"))],
) -> models.Client:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(client, key, value)
    record_audit_log(
        db,
        actor,
        action="client.update",
        entity_type="client",
        entity_id=client.id,
        details={"fields": sorted(changes.keys())},
    )
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}/anonymize", response_model=schemas.ClientRead)
def anonymize_client(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin"))],
) -> models.Client:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    had_email = client.email is not None
    client.name = "Anonymized client"
    client.email = None
    client.phone = None
    db.query(models.Consent).filter(models.Consent.client_id == client.id).update({"active": False})
    record_audit_log(
        db,
        actor,
        action="client.anonymize",
        entity_type="client",
        entity_id=client.id,
        details={"had_email": had_email},
    )
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}/export")
def export_client_data(
    client_id: int,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[models.User, Depends(require_roles("admin", "manager"))],
) -> dict:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    inquiries = (
        db.query(models.Inquiry)
        .filter(models.Inquiry.client_id == client_id)
        .order_by(models.Inquiry.created_at.desc())
        .all()
    )
    inquiry_ids = [inquiry.id for inquiry in inquiries]
    offers = []
    if inquiry_ids:
        offers = (
            db.query(models.Offer)
            .filter(models.Offer.inquiry_id.in_(inquiry_ids))
            .order_by(models.Offer.created_at.desc())
            .all()
        )

    export_data = {
        "client": schemas.ClientRead.model_validate(client).model_dump(mode="json"),
        "consents": [
            schemas.ConsentRead.model_validate(consent).model_dump(mode="json")
            for consent in db.query(models.Consent)
            .filter(models.Consent.client_id == client_id)
            .order_by(models.Consent.granted_at.desc())
            .all()
        ],
        "inquiries": [schemas.InquiryRead.model_validate(inquiry).model_dump(mode="json") for inquiry in inquiries],
        "offers": [schemas.OfferRead.model_validate(offer).model_dump(mode="json") for offer in offers],
        "activity_logs": [
            schemas.ActivityLogRead.model_validate(log).model_dump(mode="json")
            for log in db.query(models.ActivityLog)
            .filter(models.ActivityLog.client_id == client_id)
            .order_by(models.ActivityLog.logged_at.desc())
            .all()
        ],
    }
    record_audit_log(
        db,
        actor,
        action="client.export",
        entity_type="client",
        entity_id=client.id,
        details={"sections": sorted(export_data.keys())},
    )
    db.commit()
    return export_data


@router.get(
    "/{client_id}/timeline",
    response_model=list[schemas.TimelineItem],
    dependencies=[Depends(require_roles("admin", "sales", "manager"))],
)
def client_timeline(client_id: int, db: Annotated[Session, Depends(get_db)]) -> list[schemas.TimelineItem]:
    if not db.get(models.Client, client_id):
        raise HTTPException(status_code=404, detail="Client not found")

    items: list[schemas.TimelineItem] = []
    for inquiry in db.query(models.Inquiry).filter(models.Inquiry.client_id == client_id).all():
        items.append(
            schemas.TimelineItem(
                type="inquiry",
                title=f"Inquiry #{inquiry.id} ({inquiry.status})",
                timestamp=inquiry.created_at,
                data={"message": inquiry.message},
            )
        )
    for log in db.query(models.ActivityLog).filter(models.ActivityLog.client_id == client_id).all():
        items.append(
            schemas.TimelineItem(
                type="activity",
                title=f"{log.event_type} on {log.page_url}",
                timestamp=log.logged_at,
                data={"event_data": log.event_data, "time_on_page": log.time_on_page},
            )
        )
    return sorted(items, key=lambda item: item.timestamp, reverse=True)
