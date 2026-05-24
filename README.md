# DocuVerify AI

Document trust, simplified.

DocuVerify AI is an AI-powered document trust platform for recruiters, HR teams, institutions, companies, and candidates. It verifies certificates, resumes, experience letters, marksheets, and supporting documents using OCR, metadata review, QR validation, SHA-256 integrity checks, visual tamper detection, manual review workflows, and candidate-level trust scoring.

## Product Overview

DocuVerify AI helps verification teams make faster, more consistent authenticity decisions. The platform combines deterministic checks with AI-assisted review signals, then produces a clear trust score, risk level, review notes, and downloadable verification report.

## Features

- Document upload with safe filenames, file type validation, size limits, and SHA-256 hashing
- OCR extraction for PDFs and images with a modular service layer for Tesseract and EasyOCR
- Metadata review for PDF and image files using PyMuPDF, pypdf, and Pillow
- QR and certificate ID verification against institution-issued certificate records
- Hash integrity comparison for exact document match verification
- Visual tamper detection with heatmap output and suspicious region scoring
- Resume consistency checks across resumes, certificates, and experience letters
- AI Verification Agent that selects checks based on document type
- Manual review queue for medium-risk and high-risk documents
- Candidate profiles and Trust Passport scoring
- Batch verification for HR teams
- Public certificate and Trust Passport verification pages
- Institution certificate issuing, QR generation, revoke flow, and verification ledger
- Audit logs, notifications, settings, reports, and research metrics

## Architecture

```text
Users
  |
  v
React + Vite Frontend
  |  Axios / JWT
  v
FastAPI Backend
  |
  +-- Auth and role access
  +-- Document upload and storage
  +-- OCR service
  +-- Metadata service
  +-- QR verification service
  +-- Hash integrity service
  +-- Tamper detection service
  +-- Scoring and explanation services
  +-- Manual review, batch, candidate, passport, and reports
  |
  v
PostgreSQL + SQLAlchemy
```

## Tech Stack

**Frontend:** React, Vite, Tailwind CSS, Framer Motion, React Router, Axios, Lucide React, Recharts  
**Backend:** FastAPI, Python, SQLAlchemy, Pydantic Settings, JWT auth  
**Database:** PostgreSQL  
**Document Intelligence:** PyMuPDF, pypdf, Pillow, OpenCV, pytesseract, EasyOCR-ready structure, pyzbar/OpenCV QR detection  
**Reporting:** ReportLab  
**Deployment:** Docker and Docker Compose

## Local Development Setup

### 1. Clone and enter the repository

```bash
git clone <repository-url>
cd docuverify-ai
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Update the values for your database, JWT secret, frontend URL, and storage directories.

### 3. Start with Docker

```bash
docker compose up --build
```

Default service URLs:

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`

### 4. Start backend manually

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 5. Start frontend manually

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection string |
| `JWT_SECRET` | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime |
| `FRONTEND_URL` | Allowed frontend origin for CORS |
| `ALLOWED_ORIGINS` | Comma-separated allowed CORS origins |
| `MAX_UPLOAD_SIZE_MB` | Maximum accepted upload size |
| `STORAGE_PROVIDER` | `local` for development or `supabase` for cloud storage |
| `SUPABASE_URL` | Supabase workspace URL for private storage |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend-only Supabase service role key |
| `SUPABASE_BUCKET` | Private document bucket name |
| `UPLOAD_DIR` | Uploaded document storage directory |
| `PROCESSED_DIR` | Generated heatmap storage directory |
| `GENERATED_QR_DIR` | Generated QR image storage directory |
| `REPORT_DIR` | PDF report storage directory |
| `PUBLIC_BASE_URL` | Base URL used for public verification links |
| `VITE_API_BASE_URL` | Frontend API base URL |

For deployed environments, set `JWT_SECRET` to a strong private value and use managed secrets.

## API Overview

| Area | Endpoints |
| --- | --- |
| Health | `GET /api/health`, `GET /api/version` |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` |
| Documents | `POST /api/documents/upload`, `GET /api/documents/my-documents`, `GET /api/documents/{id}`, `DELETE /api/documents/{id}` |
| Verification | `POST /api/verification/{document_id}/full-check`, `POST /api/verification/{document_id}/ocr`, `POST /api/verification/{document_id}/metadata`, `POST /api/verification/{document_id}/qr-verify`, `POST /api/verification/{document_id}/hash-verify`, `POST /api/verification/{document_id}/tamper-detect` |
| Agent | `POST /api/agent/verify/{document_id}` |
| Reports | `GET /api/verification/{verification_id}/report`, `GET /api/verification/{verification_id}/explanations` |
| Institution | `POST /api/institution/certificates/issue`, `GET /api/institution/certificates`, `PATCH /api/institution/certificates/{id}/revoke` |
| Public Verification | `GET /api/public/verify/{certificate_id}`, `GET /api/public/passport/{public_token}` |
| Reviews | `POST /api/reviews/create`, `GET /api/reviews`, `GET /api/reviews/{id}`, `PATCH /api/reviews/{id}/assign`, `PATCH /api/reviews/{id}/decision`, `PATCH /api/reviews/{id}/comment` |
| Candidates | `POST /api/candidates`, `GET /api/candidates`, `GET /api/candidates/{id}`, `POST /api/candidates/{id}/documents`, `POST /api/candidates/{id}/generate-passport`, `GET /api/candidates/{id}/passport` |
| Batch | `POST /api/batch/create`, `POST /api/batch/{id}/upload`, `POST /api/batch/{id}/verify`, `GET /api/batch`, `GET /api/batch/{id}`, `GET /api/batch/{id}/results`, `GET /api/batch/{id}/export-csv` |
| Admin | `GET /api/admin/audit-logs`, `GET /api/settings`, `PATCH /api/settings` |
| Notifications | `GET /api/notifications`, `PATCH /api/notifications/{id}/read`, `PATCH /api/notifications/read-all` |
| Research Metrics | `GET /api/research/metrics` |

## Security Notes

- Use a strong `JWT_SECRET` and rotate it through your secret manager.
- Restrict CORS to trusted frontend origins.
- Store uploaded files in a private object store for production deployments.
- Scan uploaded files before long-term storage in regulated environments.
- Use HTTPS for all public traffic.
- Keep PostgreSQL, Python, Node, and native OCR/CV dependencies patched.
- Review access control before enabling public organization workspaces.
- Configure retention policies for documents, reports, and audit logs.

## Deployment Guide

Recommended production architecture:

- Vercel for the React frontend
- Render for the FastAPI backend
- Neon PostgreSQL for the database
- Supabase Storage for private document files
- HTTPS termination through a managed load balancer or reverse proxy
- Environment-specific secrets through the hosting provider
- Centralized logging and monitoring

Docker startup:

```bash
docker compose up --build
```

For managed hosting, build the frontend and serve the static bundle behind HTTPS. Run the backend as an ASGI service with a production process manager and connect it to managed PostgreSQL.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the Render, Vercel, Neon, and Supabase deployment workflow.

Deployment settings:

| Service | Setting | Value |
| --- | --- | --- |
| Vercel | Root directory | `frontend` |
| Vercel | Build command | `npm run build` |
| Vercel | Output directory | `dist` |
| Vercel | Environment | `VITE_API_BASE_URL=https://your-render-service.onrender.com/api` |
| Render | Root directory | `backend` |
| Render | Build command | `pip install -r requirements.txt` |
| Render | Start command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Neon | Connection string | `postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require` |

## Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Production startup should apply migrations before serving traffic.

## Contribution Guide

1. Create a branch for each change.
2. Keep backend changes covered by focused route or service checks.
3. Run the frontend build before opening a pull request.
4. Keep UI copy concise and product-focused.
5. Avoid exposing credentials, stack traces, or internal debug output.

## License

Add a license before public distribution.
#   D o c u V e r i f y - A I  
 #   D o c u V e r i f y - A I  
 