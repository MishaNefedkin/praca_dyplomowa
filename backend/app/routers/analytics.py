from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import require_roles
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_roles("admin", "manager"))])


@router.get("/kpi", response_model=schemas.KPIRead)
def kpi(db: Annotated[Session, Depends(get_db)]) -> schemas.KPIRead:
    inquiries_count = db.query(models.Inquiry).count()
    inquiries_with_offer = db.query(models.Offer.inquiry_id).distinct().count()
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    conversion = round((inquiries_with_offer / inquiries_count * 100), 2) if inquiries_count else 0

    return schemas.KPIRead(
        clients_count=db.query(models.Client).count(),
        new_inquiries_count=db.query(models.Inquiry).filter(models.Inquiry.status == "new").count(),
        sent_offers_count=db.query(models.Offer).filter(models.Offer.status == "sent").count(),
        inquiry_to_offer_conversion_rate=conversion,
        activities_last_24h=db.query(models.ActivityLog).filter(models.ActivityLog.logged_at >= since).count(),
    )


@router.get("/top-pages", response_model=list[schemas.TopPageRead])
def top_pages(db: Annotated[Session, Depends(get_db)]) -> list[schemas.TopPageRead]:
    rows = (
        db.query(models.ActivityLog.page_url, func.count(models.ActivityLog.id).label("visits"))
        .filter(models.ActivityLog.event_type == "page_view")
        .group_by(models.ActivityLog.page_url)
        .order_by(func.count(models.ActivityLog.id).desc())
        .limit(10)
        .all()
    )
    return [schemas.TopPageRead(page_url=row.page_url, visits=row.visits) for row in rows]


@router.get("/alerts")
def alerts(db: Annotated[Session, Depends(get_db)]) -> list[dict]:
    stale_limit = datetime.now(timezone.utc) - timedelta(days=3)
    stale_new = (
        db.query(models.Inquiry)
        .filter(models.Inquiry.status == "new", models.Inquiry.created_at <= stale_limit)
        .order_by(models.Inquiry.created_at.asc())
        .limit(20)
        .all()
    )
    return [
        {
            "type": "stale_inquiry",
            "message": f"Inquiry #{inquiry.id} requires action",
            "client_id": inquiry.client_id,
            "created_at": inquiry.created_at,
        }
        for inquiry in stale_new
    ]
