from sqlalchemy.orm import Session

from app.models import Notification, NotificationType


def create_notification(
    db: Session,
    *,
    user_id: int | None,
    title: str,
    message: str,
    type: NotificationType = NotificationType.INFO,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=type,
    )
    db.add(notification)
    return notification
