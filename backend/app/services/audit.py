from sqlalchemy.orm import Session

from .. import models


def record_audit_log(
    db: Session,
    actor: models.User,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        models.AuditLog(
            actor_user_id=actor.id,
            actor_login=actor.login,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
