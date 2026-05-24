import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
}


@dataclass(frozen=True)
class StoredFile:
    original_filename: str
    file_path: Path
    file_hash: str
    size_bytes: int


def ensure_directory(path: str | Path) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_unique_filename(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    stem = Path(original_filename).stem.lower()
    safe_stem = re.sub(r"[^a-z0-9._-]+", "-", stem).strip(".-") or "document"
    return f"{uuid4().hex}_{safe_stem}{suffix}"


def validate_upload_file(file: UploadFile) -> None:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload PDF, JPG, JPEG, or PNG.",
        )
    if file.content_type and file.content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported content type. Upload PDF, JPG, JPEG, or PNG.",
        )


async def store_upload_file(
    file: UploadFile,
    upload_dir: str | Path,
    max_size_bytes: int,
) -> StoredFile:
    """Store an uploaded document and compute a SHA-256 hash as it streams.

    Hashing gives every file a stable fingerprint. If a certificate is edited after
    upload, even by one byte, its SHA-256 value changes, which makes tampering and
    duplicate-submission detection much more reliable.
    """
    validate_upload_file(file)
    directory = ensure_directory(upload_dir)
    destination = directory / safe_unique_filename(file.filename or "document")

    digest = sha256()
    total_size = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total_size += len(chunk)
                if total_size > max_size_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File size exceeds the 10 MB limit.",
                    )
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise
    finally:
        await file.close()

    return StoredFile(
        original_filename=file.filename or destination.name,
        file_path=destination,
        file_hash=digest.hexdigest(),
        size_bytes=total_size,
    )


def delete_stored_file(path: str | Path) -> None:
    file_path = Path(path)
    if file_path.exists() and file_path.is_file():
        file_path.unlink()

