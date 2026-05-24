from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Shared declarative base for all SQLAlchemy models."""


settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_tables() -> None:
    """Create all registered tables. Intended for local setup and tests."""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_dev_columns()


def ensure_sqlite_dev_columns() -> None:
    """Add newly introduced columns to an existing SQLite database.

    Production deployments should use Alembic migrations. This helper keeps a
    developer workspace database aligned with the current schema during upgrades.
    """
    if engine.dialect.name != "sqlite":
        return

    required_columns = {
        "manual_reviews": {
            "priority": "VARCHAR(16) NOT NULL DEFAULT 'medium'",
            "final_decision": "TEXT",
        },
        "batch_verifications": {
            "completed_documents": "INTEGER NOT NULL DEFAULT 0",
            "failed_documents": "INTEGER NOT NULL DEFAULT 0",
        },
        "batch_documents": {
            "status": "VARCHAR(32) NOT NULL DEFAULT 'pending'",
            "score": "FLOAT",
            "risk_level": "VARCHAR(64)",
            "error_message": "TEXT",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        },
        "candidate_profiles": {
            "updated_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        },
        "candidate_documents": {
            "document_category": "VARCHAR(64)",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP",
        },
        "trust_passports": {
            "public_token": "VARCHAR(128)",
            "overall_score": "FLOAT NOT NULL DEFAULT 0",
            "education_score": "FLOAT NOT NULL DEFAULT 0",
            "certificate_score": "FLOAT NOT NULL DEFAULT 0",
            "experience_score": "FLOAT NOT NULL DEFAULT 0",
            "resume_score": "FLOAT NOT NULL DEFAULT 0",
            "risk_level": "VARCHAR(64) NOT NULL DEFAULT 'very_high'",
        },
        "verification_results": {
            "heatmap_path": "VARCHAR(1024)",
        },
        "users": {
            "onboarding_completed": "BOOLEAN NOT NULL DEFAULT 0",
        },
        "uploaded_documents": {
            "workspace_id": "INTEGER",
        },
    }

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in required_columns.items():
            if not inspector.has_table(table_name):
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
