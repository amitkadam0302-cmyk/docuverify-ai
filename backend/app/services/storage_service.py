from __future__ import annotations

import json
import hmac
import mimetypes
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import get_settings
from app.utils.file_storage import StoredFile, delete_stored_file, store_upload_file


@dataclass(frozen=True)
class StoredObject:
    original_filename: str
    storage_path: str
    file_hash: str
    size_bytes: int


async def upload_file(file: UploadFile) -> StoredObject:
    settings = get_settings()
    local_file = await store_upload_file(
        file=file,
        upload_dir=settings.upload_dir,
        max_size_bytes=settings.max_upload_size_bytes,
    )

    if settings.storage_provider == "local":
        return StoredObject(
            original_filename=local_file.original_filename,
            storage_path=str(local_file.file_path),
            file_hash=local_file.file_hash,
            size_bytes=local_file.size_bytes,
        )

    object_name = f"documents/{local_file.file_hash}/{local_file.file_path.name}"
    if settings.storage_provider == "supabase":
        upload_to_supabase(local_file, object_name)
        return StoredObject(local_file.original_filename, f"supabase://{object_name}", local_file.file_hash, local_file.size_bytes)

    if settings.storage_provider == "s3":
        upload_to_s3(local_file, object_name)
        return StoredObject(local_file.original_filename, f"s3://{settings.s3_bucket}/{object_name}", local_file.file_hash, local_file.size_bytes)

    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage provider is not configured.")


def delete_file(storage_path: str) -> None:
    settings = get_settings()
    if storage_path.startswith("supabase://"):
        delete_from_supabase(storage_path.removeprefix("supabase://"))
        return
    if storage_path.startswith("s3://"):
        delete_from_s3(storage_path)
        return
    delete_stored_file(storage_path)


def create_signed_url(storage_path: str, expires_in: int = 900) -> str:
    settings = get_settings()
    if storage_path.startswith("supabase://"):
        return signed_supabase_url(storage_path.removeprefix("supabase://"), expires_in)
    if storage_path.startswith("s3://"):
        return signed_s3_url(storage_path, expires_in)
    filename = Path(storage_path).name
    expires = int(time.time()) + expires_in
    signature = sign_local_preview(filename, expires)
    return f"{settings.public_base_url.rstrip('/')}/api/documents/local-preview/{filename}?expires={expires}&signature={signature}"


def validate_local_preview_signature(filename: str, expires: int, signature: str) -> bool:
    if expires < int(time.time()):
        return False
    return hmac.compare_digest(sign_local_preview(filename, expires), signature)


def sign_local_preview(filename: str, expires: int) -> str:
    settings = get_settings()
    return hmac.new(settings.secret_key.encode(), f"{filename}:{expires}".encode(), "sha256").hexdigest()


def resolve_local_path(storage_path: str) -> str:
    if storage_path.startswith("supabase://"):
        return download_supabase_to_cache(storage_path.removeprefix("supabase://"))
    if storage_path.startswith("s3://"):
        return download_s3_to_cache(storage_path)
    return storage_path


def upload_to_supabase(local_file: StoredFile, object_name: str) -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_bucket:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase storage is not configured.")
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}/{urllib.parse.quote(object_name)}"
    headers = supabase_headers(local_file.file_path)
    request = urllib.request.Request(url, data=local_file.file_path.read_bytes(), headers=headers, method="POST")
    try:
        urllib.request.urlopen(request, timeout=30).read()
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            request = urllib.request.Request(url, data=local_file.file_path.read_bytes(), headers=headers, method="PUT")
            urllib.request.urlopen(request, timeout=30).read()
        else:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Cloud storage upload failed.") from exc


def delete_from_supabase(object_name: str) -> None:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_bucket:
        return
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}"
    payload = json.dumps({"prefixes": [object_name]}).encode()
    request = urllib.request.Request(url, data=payload, headers=supabase_json_headers(), method="DELETE")
    try:
        urllib.request.urlopen(request, timeout=15).read()
    except urllib.error.URLError:
        return


def signed_supabase_url(object_name: str, expires_in: int) -> str:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_bucket:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Supabase storage is not configured.")
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/sign/{settings.supabase_bucket}/{urllib.parse.quote(object_name)}"
    request = urllib.request.Request(
        url,
        data=json.dumps({"expiresIn": expires_in}).encode(),
        headers=supabase_json_headers(),
        method="POST",
    )
    try:
        response = json.loads(urllib.request.urlopen(request, timeout=15).read().decode())
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Signed URL creation failed.") from exc
    signed_url = response.get("signedURL") or response.get("signedUrl")
    if not signed_url:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Signed URL creation failed.")
    return f"{settings.supabase_url.rstrip('/')}/storage/v1{signed_url}"


def download_supabase_to_cache(object_name: str) -> str:
    settings = get_settings()
    cache_path = cache_file_path(object_name)
    if cache_path.exists():
        return str(cache_path)
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}/{urllib.parse.quote(object_name)}"
    request = urllib.request.Request(url, headers=supabase_json_headers(), method="GET")
    try:
        cache_path.write_bytes(urllib.request.urlopen(request, timeout=30).read())
    except urllib.error.URLError as exc:
        raise FileNotFoundError(object_name) from exc
    return str(cache_path)


def upload_to_s3(local_file: StoredFile, object_name: str) -> None:
    settings = get_settings()
    try:
        import boto3
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 support requires boto3.") from exc
    client = boto3.client(
        "s3",
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )
    client.upload_file(str(local_file.file_path), settings.s3_bucket, object_name)


def delete_from_s3(storage_path: str) -> None:
    settings = get_settings()
    try:
        import boto3
    except ImportError:
        return
    bucket, key = parse_s3_path(storage_path)
    boto3.client("s3", region_name=settings.s3_region).delete_object(Bucket=bucket, Key=key)


def signed_s3_url(storage_path: str, expires_in: int) -> str:
    settings = get_settings()
    try:
        import boto3
    except ImportError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="S3 support requires boto3.") from exc
    bucket, key = parse_s3_path(storage_path)
    return boto3.client("s3", region_name=settings.s3_region).generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


def download_s3_to_cache(storage_path: str) -> str:
    settings = get_settings()
    bucket, key = parse_s3_path(storage_path)
    cache_path = cache_file_path(key)
    if cache_path.exists():
        return str(cache_path)
    try:
        import boto3
    except ImportError as exc:
        raise FileNotFoundError(storage_path) from exc
    boto3.client("s3", region_name=settings.s3_region).download_file(bucket, key, str(cache_path))
    return str(cache_path)


def parse_s3_path(storage_path: str) -> tuple[str, str]:
    clean = storage_path.removeprefix("s3://")
    bucket, key = clean.split("/", 1)
    return bucket, key


def cache_file_path(object_name: str) -> Path:
    settings = get_settings()
    cache_dir = Path(settings.storage_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(object_name).suffix or ".bin"
    return cache_dir / f"{sha256(object_name.encode()).hexdigest()}{suffix}"


def supabase_headers(path: Path) -> dict[str, str]:
    headers = supabase_json_headers()
    headers["content-type"] = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    headers["x-upsert"] = "true"
    return headers


def supabase_json_headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key or "",
        "content-type": "application/json",
    }
