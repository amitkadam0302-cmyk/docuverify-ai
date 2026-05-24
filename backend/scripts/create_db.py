from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import create_database_tables


if __name__ == "__main__":
    create_database_tables()
    print("Database tables created successfully.")
