# Predictive Maintenance Backend

FastAPI backend for the Fathom Predictive Maintenance Agent.

## Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- MongoDB (Atlas or local)

### Setup

```bash
# 1. Clone and navigate
cd predictive-maintenance-backend

# 2. Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your values (see Configuration below)

# 5. Run development server
uvicorn backend.main:app --reload --port 8000
```

Server runs at `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/v1/health`

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
# Required
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/fathom
JWT_SECRET=your-32-char-secret-key-here

# Optional
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
GRADIO_API_URL=https://your-gradio-space.hf.space/gradio_api
BOOTSTRAP_ADMIN_EMAIL=admin@company.com
BOOTSTRAP_ADMIN_PASSWORD=secure-password
BOOTSTRAP_ADMIN_SECRET=one-time-bootstrap-secret
```

### Generate JWT Secret
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## First Admin Setup

After starting the server, create the first admin user:

```bash
curl -X POST http://localhost:8000/api/v1/auth/bootstrap-admin \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"secure-password","full_name":"Admin User","bootstrap_secret":"your-bootstrap-secret"}'
```

Or visit `http://localhost:8000/docs` and use the `/auth/bootstrap-admin` endpoint.

## API Endpoints

| Resource | Endpoints |
|----------|-----------|
| **Auth** | `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`, `POST /api/v1/auth/register` (admin) |
| **Missions** | `GET/POST /api/v1/missions`, `GET/PATCH/DELETE /api/v1/missions/{id}`, `POST /api/v1/missions/{id}/assign-workers` |
| **Machines** | `GET/POST /api/v1/machines`, `GET/PATCH/DELETE /api/v1/machines/{id}`, `POST /api/v1/machines/{id}/assign-workers` |
| **Assessments** | `POST /api/v1/assessments/predict`, `GET /api/v1/assessments`, `GET /api/v1/assessments/{id}` |
| **Alerts** | `GET /api/v1/alerts`, `GET /api/v1/alerts/{id}`, `PATCH /api/v1/alerts/{id}/acknowledge`, `PATCH /api/v1/alerts/{id}/resolve` |
| **Reports** | `POST /api/v1/reports`, `GET /api/v1/reports`, `GET /api/v1/reports/{id}`, `GET /api/v1/reports/{id}/download` |
| **Health** | `GET /api/v1/health`, `GET /api/v1/health/detailed`, `GET /api/v1/version` |

## Roles & Permissions

| Feature | Admin | Supervisor | Worker |
|---------|-------|------------|--------|
| User Management | ✓ | ✗ | ✗ |
| Mission CRUD | ✓ | ✗ | ✗ |
| Machine CRUD | ✓ | ✗ | ✗ |
| Assign Workers | ✓ | ✓ | ✗ |
| Run Prediction | ✓ | ✓ (assigned) | ✓ (assigned) |
| View Alerts | ✓ | ✓ (assigned) | ✓ (assigned) |
| Acknowledge Alerts | ✓ | ✓ | ✓ (assigned) |
| Resolve Alerts | ✓ | ✓ | ✗ |
| Generate Reports | ✓ | ✓ (assigned) | ✓ (assigned) |

## Project Structure

```
backend/
├── config.py              # Settings (pydantic-settings)
├── main.py                # FastAPI app + route registration
├── db/
│   └── mongodb.py         # Motor async client + indexes
├── models/
│   ├── user.py            # User, roles, tokens
│   ├── mission.py         # Mission
│   ├── machine.py         # Machine
│   ├── assessment.py      # Assessment
│   ├── alert.py           # Alert
│   └── report.py          # Report
├── schemas/
│   └── auth.py            # Auth request/response models
├── services/
│   ├── auth.py            # JWT, bcrypt, RBAC dependencies
│   ├── assessment.py      # Assessment persistence
│   ├── alert.py           # Alert auto-creation
│   └── fallback.py        # Simulated physics engine
├── routes/
│   ├── auth.py
│   ├── missions.py
│   ├── machines.py
│   ├── assessments.py
│   ├── alerts.py
│   ├── reports.py
│   └── health.py
└── lib/
    └── derived.py         # Shared calculations
```

## Production Deployment (Simple)

### Option 1: Direct on VM
```bash
# On server
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Option 2: Process Manager (systemd/supervisor)
Create `/etc/systemd/system/fathom-backend.service`:
```ini
[Unit]
Description=Fathom Predictive Maintenance Backend
After=network.target

[Service]
Type=exec
User=www-data
WorkingDirectory=/opt/fathom-backend
Environment=PATH=/opt/fathom-backend/.venv/bin
ExecStart=/opt/fathom-backend/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Option 3: Docker (if needed later)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY src ./src
COPY models ./models
COPY configs ./configs
COPY data ./data
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Frontend Integration

Frontend runs separately at `http://localhost:5173`:
```bash
cd ../predictive-maintenance-agent-frontend
npm install
npm run dev
```

Set `VITE_API_BASE=http://localhost:8000` in frontend `.env` for local development.

## License

Internal use only.