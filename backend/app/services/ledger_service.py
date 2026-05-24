from datetime import datetime, timezone
from hashlib import sha256

from sqlalchemy.orm import Session

from app.models import VerificationLedger


def create_ledger_entry(
    db: Session,
    certificate_id: str,
    action: str,
    payload_hash: str,
) -> VerificationLedger:
    previous_entry = (
        db.query(VerificationLedger)
        .filter_by(certificate_id=certificate_id)
        .order_by(VerificationLedger.id.desc())
        .first()
    )
    previous_hash = previous_entry.current_hash if previous_entry else None
    timestamp = datetime.now(timezone.utc).isoformat()
    raw = f"{certificate_id}:{action}:{payload_hash}:{previous_hash or 'GENESIS'}:{timestamp}"
    ledger = VerificationLedger(
        certificate_id=certificate_id,
        previous_hash=previous_hash,
        current_hash=sha256(raw.encode()).hexdigest(),
        action=action,
    )
    db.add(ledger)
    db.flush()
    return ledger

