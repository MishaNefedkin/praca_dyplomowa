from sqlalchemy.orm import Session

from .. import models
from ..schemas import InquiryCreate


def create_inquiry_from_contact_form(db: Session, payload: InquiryCreate) -> models.Inquiry:
    client = db.query(models.Client).filter(models.Client.email == payload.email).first()
    link_tracking_session = False
    if client is None:
        client = models.Client(
            name=payload.name,
            email=str(payload.email),
            phone=payload.phone,
            session_id=payload.session_id,
        )
        db.add(client)
        db.flush()
        link_tracking_session = True
    else:
        link_tracking_session = client.session_id == payload.session_id

    inquiry = models.Inquiry(client_id=client.id, message=payload.message, status="new")
    db.add(inquiry)
    db.add(models.Consent(client_id=client.id, scope=payload.consent_scope, active=True))
    if link_tracking_session:
        db.query(models.ActivityLog).filter(
            models.ActivityLog.session_id == payload.session_id,
            models.ActivityLog.client_id.is_(None),
        ).update({"client_id": client.id}, synchronize_session=False)
    db.commit()
    db.refresh(inquiry)
    return inquiry
