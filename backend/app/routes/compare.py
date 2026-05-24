from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_recruiter_or_admin
from app.models import UploadedDocument, User
from app.schemas.workflows import DocumentComparisonRequest, DocumentComparisonResponse
from app.services.compare_service import compare_documents

router = APIRouter(prefix="/compare", tags=["document comparison"])


@router.post("/documents", response_model=DocumentComparisonResponse)
def compare_uploaded_documents(
    payload: DocumentComparisonRequest,
    current_user: User = Depends(require_recruiter_or_admin),
    db: Session = Depends(get_db),
) -> DocumentComparisonResponse:
    left = db.get(UploadedDocument, payload.left_document_id)
    right = db.get(UploadedDocument, payload.right_document_id)
    if left is None or right is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both documents were not found.")
    return DocumentComparisonResponse(**compare_documents(left.file_path, right.file_path))
