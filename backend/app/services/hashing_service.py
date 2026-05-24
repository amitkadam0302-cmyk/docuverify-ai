from hashlib import sha256
from pathlib import Path

from app.services.storage_service import resolve_local_path


def calculate_sha256(file_path: str | Path, chunk_size: int = 1024 * 1024) -> str:
    """Calculate a SHA-256 hash for a file without loading it all into memory."""
    digest = sha256()
    with Path(resolve_local_path(str(file_path))).open("rb") as file:
        for chunk in iter(lambda: file.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()
