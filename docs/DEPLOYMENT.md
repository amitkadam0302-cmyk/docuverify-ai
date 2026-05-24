# Production Deployment Guide

This guide targets Vercel for the React frontend, Render for the FastAPI backend, Neon PostgreSQL for the database, and Supabase Storage for private document storage.

## 1. Neon PostgreSQL

1. Create a Neon database.
2. Copy the pooled connection string.
3. Use the SQLAlchemy format:

```text
postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE?sslmode=require
```

## 2. Supabase Storage

1. Create a private bucket for document files.
2. Save:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_BUCKET`
3. Keep the service role key only on the backend.

## 3. Render Backend

Create a Render Web Service from `backend/`.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Required environment variables:

```text
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql+psycopg2://...
JWT_SECRET=<strong secret>
FRONTEND_URL=https://your-vercel-domain.vercel.app
ALLOWED_ORIGINS=https://your-vercel-domain.vercel.app
PUBLIC_BASE_URL=https://your-render-service.onrender.com
STORAGE_PROVIDER=supabase
SUPABASE_URL=https://your-workspace.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service role key>
SUPABASE_BUCKET=docuverify-documents
CONTACT_EMAIL=support@yourdomain.com
```

## 4. Vercel Frontend

Create a Vercel app from `frontend/`.

Build command:

```bash
npm run build
```

Output directory:

```text
dist
```

Required environment variables:

```text
VITE_API_BASE_URL=https://your-render-service.onrender.com/api
VITE_CONTACT_EMAIL=support@yourdomain.com
```

## 5. Database Migrations

Create migrations during development:

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
```

Apply migrations:

```bash
alembic upgrade head
```

Production startup should run `alembic upgrade head` before the ASGI server starts.

## 6. Storage

Use `STORAGE_PROVIDER=supabase` for production.

Supported providers:

- `local`
- `supabase`
- `s3`

Private document links should be delivered through signed URLs only.

## 7. Pre-Launch Checklist

- Frontend build passes.
- Backend starts and `/api/health` returns `ok`.
- Neon database is connected.
- Alembic migrations are applied.
- Supabase private bucket is configured.
- `JWT_SECRET` is strong and private.
- CORS points to the Vercel domain.
- File upload limit is enforced.
- PDF, JPG, JPEG, and PNG are the only accepted upload types.
- Public legal pages are linked.
- HTTPS is enabled on Vercel and Render.
