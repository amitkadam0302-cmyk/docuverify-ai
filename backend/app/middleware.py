import logging
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger("docuverify.api")
_rate_windows: dict[str, deque[float]] = defaultdict(deque)


def register_production_middleware(app: FastAPI) -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id

        limited_response = check_rate_limit(request)
        if limited_response is not None:
            return limited_response

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled request error",
                extra={"request_id": request_id, "path": request.url.path, "method": request.method},
            )
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


def check_rate_limit(request: Request) -> JSONResponse | None:
    settings = get_settings()
    path = request.url.path
    if path in {f"{settings.api_prefix}/auth/login", f"{settings.api_prefix}/auth/register"}:
        limit = settings.auth_rate_limit_per_minute
    elif path == f"{settings.api_prefix}/documents/upload" or path.startswith(f"{settings.api_prefix}/batch/"):
        limit = settings.upload_rate_limit_per_minute
    else:
        return None

    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:{path}"
    now = time.time()
    window = _rate_windows[key]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Please try again shortly."},
            headers={"retry-after": "60"},
        )
    window.append(now)
    return None
