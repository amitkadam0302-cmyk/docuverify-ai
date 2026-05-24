# DocuVerify AI Product Overview

DocuVerify AI is an AI-powered document trust platform for recruiters, HR teams, institutions, companies, and candidates. It verifies certificates, resumes, experience letters, marksheets, and supporting documents through a multi-layer authenticity workflow.

## Positioning

Document trust, simplified.

DocuVerify AI helps verification teams reduce manual effort, identify suspicious documents, and create consistent review records. The platform combines OCR, metadata review, QR validation, SHA-256 integrity checks, visual tamper detection, and candidate-level trust scoring.

## Core Workflows

### Document Verification

1. Upload a PDF or image document.
2. Extract text and structured fields.
3. Review metadata, QR content, hash integrity, and visual tamper signals.
4. Generate a trust score, risk level, and final decision.
5. Download a verification report or send the case to manual review.

### Institution Certificate Issuing

1. Institution admin issues a certificate record.
2. The platform creates a QR code and verification link.
3. Each certificate action is added to a tamper-evident ledger.
4. Recruiters and candidates can validate the certificate through public verification.

### Candidate Trust Passport

1. Verification teams create a candidate profile.
2. Documents are linked to the profile.
3. The platform calculates document-level and candidate-level trust scores.
4. A public Trust Passport can be shared with recruiters.

### Manual Review

1. Medium-risk and high-risk results can be routed to review.
2. Reviewers inspect the score, fraud flags, OCR text, and heatmap.
3. The reviewer records an approval, rejection, or request for more information.

## Key Modules

- OCR Extraction: extracts raw text and key fields from PDF and image documents.
- Metadata Review: checks creation dates, modification dates, author data, creator software, and image metadata.
- QR Verification: reads QR values and validates certificate IDs against stored records.
- Hash Integrity: compares SHA-256 hashes for exact file match verification.
- Tamper Detection: highlights visual regions with compression, blur, edge, noise, or pasted-shape signals.
- Resume Consistency: compares resume claims against supporting certificates and experience letters.
- Scoring Engine: combines verification signals into a trust score and risk level.
- Explanation Engine: turns flags into clear issue summaries and review actions.

## System Design

```text
Frontend
  React + Vite + Tailwind + Framer Motion
        |
        v
Backend API
  FastAPI + SQLAlchemy + JWT access control
        |
        +-- Document services
        +-- Verification services
        +-- Review workflows
        +-- Reporting services
        |
        v
Database
  PostgreSQL
```

## Trust Signals

- Institution record match
- Certificate ID validation
- QR status
- Hash status
- OCR consistency
- Metadata status
- Tamper status
- Review decision history

## Evaluation Metrics

DocuVerify AI includes a metrics dashboard for monitoring OCR accuracy, QR success rate, hash match rate, tamper detection precision, and overall fraud classification quality. These metrics help teams tune verification rules and track platform performance.

## Deployment Notes

For production environments, use managed PostgreSQL, private object storage, HTTPS, strong JWT secrets, restricted CORS origins, centralized logs, and clear retention policies for uploaded documents and generated reports.
