import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import SystemSettings, User, UserRole
from app.schemas.auth import UserResponse
from app.schemas.workflows import SettingsProfileRequest, SystemSettingsResponse, SystemSettingsUpdateRequest

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_SETTINGS: dict[str, Any] = {
    "auto_manual_review_threshold": 74,
    "high_risk_threshold": 54,
    "allowed_file_types": ["pdf", "jpg", "jpeg", "png"],
    "max_upload_size_mb": 10,
    "require_qr_validation": False,
    "require_hash_match": False,
}


@router.get("", response_model=SystemSettingsResponse)
def get_system_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SystemSettingsResponse:
    return SystemSettingsResponse(settings=load_settings(db))


@router.patch("", response_model=SystemSettingsResponse)
def update_system_settings(
    payload: SystemSettingsUpdateRequest,
    current_user: User = Depends(require_role(UserRole.INSTITUTION_ADMIN, UserRole.COMPANY_ADMIN, UserRole.SUPER_ADMIN)),
    db: Session = Depends(get_db),
) -> SystemSettingsResponse:
    settings = load_settings(db)
    settings.update(payload.settings)
    for key, value in settings.items():
        row = db.query(SystemSettings).filter_by(key=key).one_or_none()
        if row is None:
            row = SystemSettings(key=key, value=json.dumps(value), updated_by=current_user.id)
            db.add(row)
        else:
            row.value = json.dumps(value)
            row.updated_by = current_user.id
    db.commit()
    return SystemSettingsResponse(settings=load_settings(db))


@router.patch("/profile", response_model=UserResponse)
def update_profile_settings(
    payload: SettingsProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if payload.full_name:
        current_user.full_name = payload.full_name
    db.commit()
    db.refresh(current_user)
    return current_user


def load_settings(db: Session) -> dict[str, Any]:
    settings = dict(DEFAULT_SETTINGS)
    for row in db.query(SystemSettings).all():
        try:
            settings[row.key] = json.loads(row.value)
        except json.JSONDecodeError:
            settings[row.key] = row.value
    return settings
