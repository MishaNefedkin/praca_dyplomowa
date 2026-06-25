from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[schemas.ClientRead])
def list_clients(db: Annotated[Session, Depends(get_db)]) -> list[models.Client]:
    return db.query(models.Client).order_by(models.Client.created_at.desc()).all()


@router.post("", response_model=schemas.ClientRead)
def create_client(payload: schemas.ClientCreate, db: Annotated[Session, Depends(get_db)]) -> models.Client:
    if db.query(models.Client).filter(models.Client.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Client with this email already exists")
    client = models.Client(**payload.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=schemas.ClientRead)
def get_client(client_id: int, db: Annotated[Session, Depends(get_db)]) -> models.Client:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}", response_model=schemas.ClientRead)
def update_client(client_id: int, payload: schemas.ClientUpdate, db: Annotated[Session, Depends(get_db)]) -> models.Client:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(client, key, value)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}/anonymize", response_model=schemas.ClientRead)
def anonymize_client(client_id: int, db: Annotated[Session, Depends(get_db)]) -> models.Client:
    client = db.get(models.Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    client.name = "Anonimized client"
    client.email = None
    client.phone = None
    db.query(models.Consent).filter(models.Consent.client_id == client.id).update({"active": False})
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}/timeline", response_model=list[schemas.TimelineItem])
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
