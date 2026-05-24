from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def unauthorized_error(detail: str = "Authentication credentials are invalid.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_error(detail: str = "You do not have permission to perform this action.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise unauthorized_error()
        user_pk = int(user_id)
    except (JWTError, ValueError) as exc:
        raise unauthorized_error() from exc

    user = db.get(User, user_pk)
    if user is None or not user.is_active:
        raise unauthorized_error("User account is inactive or no longer exists.")
    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Return a dependency that allows only the supplied roles."""

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role == UserRole.SUPER_ADMIN:
            return current_user
        if current_user.role not in allowed_roles:
            allowed = ", ".join(role.value for role in allowed_roles)
            raise forbidden_error(f"Required role: {allowed}.")
        return current_user

    return role_dependency


def require_institution_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in {UserRole.INSTITUTION_ADMIN, UserRole.SUPER_ADMIN}:
        raise forbidden_error("Institution administrator access is required.")
    return current_user


def require_recruiter_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    allowed_roles = {
        UserRole.RECRUITER,
        UserRole.INSTITUTION_ADMIN,
        UserRole.COMPANY_ADMIN,
        UserRole.SUPER_ADMIN,
    }
    if current_user.role not in allowed_roles:
        raise forbidden_error("Recruiter or administrator access is required.")
    return current_user


def is_admin(user: User) -> bool:
    return user.role in {
        UserRole.INSTITUTION_ADMIN,
        UserRole.COMPANY_ADMIN,
        UserRole.SUPER_ADMIN,
    }
