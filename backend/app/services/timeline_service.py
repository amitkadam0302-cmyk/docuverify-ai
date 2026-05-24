from sqlalchemy.orm import Session

from app.models import VerificationEvent, VerificationEventStatus


def add_verification_event(
    db: Session,
    *,
    document_id: int,
    event_type: str,
    event_message: str,
    status: VerificationEventStatus = VerificationEventStatus.COMPLETED,
) -> VerificationEvent:
    event = VerificationEvent(
        document_id=document_id,
        event_type=event_type,
        event_message=event_message,
        status=status,
    )
    db.add(event)
    db.flush()
    return event
