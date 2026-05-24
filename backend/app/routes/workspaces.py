from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Workspace, WorkspaceMember, WorkspaceMemberStatus, WorkspaceRole
from app.schemas.workflows import (
    WorkspaceCreateRequest,
    WorkspaceInviteRequest,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleRequest,
    WorkspaceResponse,
    WorkspaceUpdateRequest,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace = Workspace(name=payload.name, owner_id=current_user.id, plan=payload.plan)
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
    db.refresh(workspace)
    return serialize_workspace(workspace)


@router.get("/current", response_model=WorkspaceResponse)
def get_current_workspace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace = current_workspace(db, current_user)
    return serialize_workspace(workspace)


@router.patch("/current", response_model=WorkspaceResponse)
def update_current_workspace(
    payload: WorkspaceUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceResponse:
    workspace = current_workspace(db, current_user)
    ensure_workspace_admin(db, workspace, current_user)
    if payload.name:
        workspace.name = payload.name
    if payload.plan:
        workspace.plan = payload.plan
    db.commit()
    db.refresh(workspace)
    return serialize_workspace(workspace)


@router.post("/invite", response_model=WorkspaceMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_workspace_member(
    payload: WorkspaceInviteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMemberResponse:
    workspace = current_workspace(db, current_user)
    ensure_workspace_admin(db, workspace, current_user)
    user = db.query(User).filter_by(email=payload.email.strip().lower()).one_or_none()
    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id if user else None,
        role=payload.role,
        status=WorkspaceMemberStatus.ACTIVE if user else WorkspaceMemberStatus.INVITED,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return serialize_member(member)


@router.get("/members", response_model=list[WorkspaceMemberResponse])
def list_workspace_members(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkspaceMemberResponse]:
    workspace = current_workspace(db, current_user)
    return [serialize_member(member) for member in workspace.members]


@router.patch("/members/{member_id}/role", response_model=WorkspaceMemberResponse)
def update_member_role(
    member_id: int,
    payload: WorkspaceMemberRoleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceMemberResponse:
    workspace = current_workspace(db, current_user)
    ensure_workspace_admin(db, workspace, current_user)
    member = db.get(WorkspaceMember, member_id)
    if member is None or member.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found.")
    member.role = payload.role
    db.commit()
    db.refresh(member)
    return serialize_member(member)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    member_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    workspace = current_workspace(db, current_user)
    ensure_workspace_admin(db, workspace, current_user)
    member = db.get(WorkspaceMember, member_id)
    if member is None or member.workspace_id != workspace.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace member not found.")
    db.delete(member)
    db.commit()


def current_workspace(db: Session, user: User) -> Workspace:
    membership = db.query(WorkspaceMember).filter_by(user_id=user.id, status=WorkspaceMemberStatus.ACTIVE).first()
    if membership:
        return membership.workspace
    workspace = Workspace(name=f"{user.full_name}'s Workspace", owner_id=user.id, plan="starter")
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=WorkspaceRole.OWNER, status=WorkspaceMemberStatus.ACTIVE))
    db.commit()
    db.refresh(workspace)
    return workspace


def ensure_workspace_admin(db: Session, workspace: Workspace, user: User) -> None:
    member = db.query(WorkspaceMember).filter_by(workspace_id=workspace.id, user_id=user.id).one_or_none()
    if member is None or member.role not in {WorkspaceRole.OWNER, WorkspaceRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace admin access is required.")


def serialize_workspace(workspace: Workspace) -> WorkspaceResponse:
    return WorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        owner_id=workspace.owner_id,
        plan=workspace.plan,
        created_at=workspace.created_at,
        updated_at=workspace.updated_at,
        members=[serialize_member(member) for member in workspace.members],
    )


def serialize_member(member: WorkspaceMember) -> WorkspaceMemberResponse:
    return WorkspaceMemberResponse(
        id=member.id,
        workspace_id=member.workspace_id,
        user_id=member.user_id,
        role=member.role,
        status=member.status,
        created_at=member.created_at,
        user_email=member.user.email if member.user else None,
        full_name=member.user.full_name if member.user else None,
    )
