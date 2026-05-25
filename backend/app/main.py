from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import create_database_tables
from app.middleware import register_production_middleware
from app.routes import api_router

settings = get_settings()


app = FastAPI(
    title="DocuVerify AI API",
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "DocuVerify AI API is running"}


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def register_development_bootstrap(app: FastAPI) -> None:
    if settings.environment.lower() == "production":
        return

    @app.on_event("startup")
    def create_local_tables() -> None:
        create_database_tables()


def init_monitoring() -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        return
    sentry_sdk.init(dsn=settings.sentry_dsn, environment=settings.environment)


def mount_static_directories(app: FastAPI) -> None:
    """Expose generated verification assets such as QR images and tamper heatmaps."""
    for route_path, directory in {
        "/processed": settings.processed_dir,
        "/generated_qr": settings.generated_qr_dir,
    }.items():
        Path(directory).mkdir(parents=True, exist_ok=True)
        app.mount(route_path, StaticFiles(directory=directory), name=route_path.strip("/"))


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent JSON responses for common API failures."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "path": str(request.url.path)},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request validation failed.",
                "errors": exc.errors(),
                "path": str(request.url.path),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        if settings.debug:
            detail = str(exc)
        else:
            detail = "A database error occurred."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail, "path": str(request.url.path)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        if settings.debug:
            detail = str(exc)
        else:
            detail = "An unexpected server error occurred."
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": detail, "path": str(request.url.path)},
        )

init_monitoring()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
register_production_middleware(app)
register_development_bootstrap(app)

# Keep application-level health routes above, then attach the feature routers.
app.include_router(api_router, prefix=settings.api_prefix)
mount_static_directories(app)
