# Deployment Guide

## Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### MongoDB

Start a local MongoDB instance (default port 27017) or set `MONGO_URI` in `backend/.env` to a MongoDB Atlas connection string.

---

## Production Checklist

### Backend

- Set `OPENROUTER_API_KEY` in environment (not in `.env` file for production)
- Set `MONGO_URI` to a production MongoDB Atlas URI with authentication
- Set `CORS_ORIGINS` to your actual frontend domain
- Run with a production ASGI server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

- Add authentication middleware (JWT) before exposing to the internet
- Move file uploads to object storage (S3 or equivalent) — replace local path in `upload.py`
- Enable MongoDB Atlas IP allowlist

### Frontend

```bash
cd frontend
npm run build
```

Serve the `build/` directory from a static host (S3 + CloudFront, Vercel, Netlify, etc.).

Set `REACT_APP_API_URL` in your hosting environment to point to the production backend URL.

### Environment Variables (Production)

| Variable | Where to set |
|---|---|
| `OPENROUTER_API_KEY` | Backend server environment |
| `MONGO_URI` | Backend server environment |
| `DATABASE_NAME` | Backend server environment |
| `CORS_ORIGINS` | Backend server environment |
| `REACT_APP_API_URL` | Frontend build environment |

---

## Docker (Optional)

A minimal `docker-compose.yml` for local development with MongoDB:

```yaml
version: '3.8'
services:
  mongo:
    image: mongo:6
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGO_URI=mongodb://mongo:27017
      - DATABASE_NAME=water_stewardship
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
    depends_on:
      - mongo

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    environment:
      - REACT_APP_API_URL=http://localhost:8000

volumes:
  mongo_data:
```

---

## WRI Data Loading

The WRI Aqueduct data must be loaded once before the risk assessment features work.

```bash
python scripts/ingest_wri.py \
  --mongo-uri mongodb://localhost:27017 \
  --db water_stewardship \
  --baseline /path/to/baseline_annual.csv \
  --future   /path/to/future_projections.csv \
  --drop
```

Expected load times (approximate):
- Baseline annual: ~2–5 minutes for ~500K records
- Future projections: ~1–2 minutes

After loading, verify with:

```bash
curl http://localhost:8000/api/wri/stats
```

---

## Health Checks

| Endpoint | Expected Response |
|---|---|
| `GET /` | `{"status": "running"}` |
| `GET /health` | `{"status": "healthy"}` |
| `GET /api/wri/stats` | WRI record counts |
| `GET /api/docs` | Swagger UI |
