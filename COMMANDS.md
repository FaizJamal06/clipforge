# ClipForge — Run Commands

## Backend (FastAPI)

The backend is a Python FastAPI app located in the `backend/` directory.

### 1. Activate the virtual environment

```powershell
# Windows (PowerShell)
cd backend
.\venv\Scripts\Activate.ps1
```

### 2. Install dependencies (first time only)

```powershell
pip install -r requirements.txt
```

### 3. Start the server

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs available at: http://localhost:8000/docs
- Health check: http://localhost:8000/health

---

## Frontend (Next.js)

The frontend is a Next.js app located in the `frontend/` directory.

### 1. Install dependencies (first time only)

```powershell
cd frontend
npm install
```

### 2. Start the dev server

```powershell
npm run dev
```

- App available at: http://localhost:3000

---

## Running Both Together

Open **two separate terminals** and run each command in its own terminal:

| Terminal | Command |
|----------|---------|
| Terminal 1 (Backend) | `cd backend && .\venv\Scripts\Activate.ps1 && uvicorn app.main:app --reload` |
| Terminal 2 (Frontend) | `cd frontend && npm run dev` |
