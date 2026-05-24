from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, UserRole
from app.schemas.auth import OnboardingCompleteRequest, TokenResponse, UserRegisterRequest, UserResponse
from app.models import Workspace, WorkspaceMember, WorkspaceMemberStatus, WorkspaceRole
from app.services.audit_service import log_action
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

SELF_SERVICE_ROLES = {UserRole.STUDENT, UserRole.RECRUITER}


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    if payload.role not in SELF_SERVICE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin roles must be provisioned by an existing administrator.",
        )

    existing_user = db.query(User).filter_by(email=payload.email).one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    email = form_data.username.strip().lower()
    user = db.query(User).filter_by(email=email).one_or_none()
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        claims={"role": user.role.value, "email": user.email},
    )
    log_action(
        db,
        user=user,
        action="user_login",
        entity_type="user",
        entity_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return TokenResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/onboarding", response_model=UserResponse)
def complete_onboarding(
    payload: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    workspace_name = payload.workspace_name or f"{current_user.full_name}'s Workspace"
    membership = db.query(WorkspaceMember).filter_by(user_id=current_user.id).first()
    if membership is None:
        workspace = Workspace(name=workspace_name, owner_id=current_user.id, plan="starter")
        db.add(workspace)
        db.flush()
        db.add(
            WorkspaceMember(
                workspace_id=workspace.id,
                user_id=current_user.id,
                role=WorkspaceRole.OWNER,
                status=WorkspaceMemberStatus.ACTIVE,
            )
        )
    current_user.onboarding_completed = True
    db.commit()
    db.refresh(current_user)
    return current_user
