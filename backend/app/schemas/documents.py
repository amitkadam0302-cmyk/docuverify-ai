from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DocumentProcessingStatus, DocumentType


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uploaded_by: int | None
    workspace_id: int | None = None
    document_type: DocumentType
    original_filename: str
    file_hash: str
    upload_time: datetime
    processing_status: DocumentProcessingStatus


class DocumentUploadResponse(BaseModel):
    document_id: int
    original_filename: str
    file_hash: str
    document_type: DocumentType
    processing_status: DocumentProcessingStatus


class DocumentSignedUrlResponse(BaseModel):
    document_id: int
    signed_url: str
    expires_in: int
