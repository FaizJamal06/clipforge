# ClipForge AI ⚡

> AI-powered podcast clipping that identifies viral 40–60 second moments and generates frame-perfect editing blueprints — in seconds.

**[Live App](https://clipforge-eosin.vercel.app)** · **[API Health](https://clipforge-production-4a6f.up.railway.app/health)** · **[API Docs](https://clipforge-production-4a6f.up.railway.app/docs)**

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐     ┌───────────┐
│   Next.js    │────▶│              FastAPI Backend                 │────▶│ PostgreSQL│
│   Frontend   │◀────│                                              │◀────│   (Prod)  │
│   (Vercel)   │ SSE │  ┌──────────────────────────────────────┐    │     └───────────┘
│              │     │  │       LangGraph Pipeline              │    │
│              │     │  │                                        │    │
│              │     │  │  Input → Transcript → Processing →    │    │
│              │     │  │  Clip Discovery → Validation →        │    │
│              │     │  │  Editing Plan → Output Formatter      │    │
│              │     │  │         ↑              |               │    │
│              │     │  │         └── retry ─────┘               │    │
│              │     │  └──────────────────────────────────────┘    │
│              │     │                    │                          │
│              │     │                    ▼                          │
│              │     │            ┌──────────────┐                  │
│              │     │            │ Google Gemini │                  │
│              │     │            │   (LLM API)  │                  │
│              │     │            └──────────────┘                  │
└─────────────┘     └──────────────────────────────────────────────┘
    Vercel                         Railway
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Orchestration | LangGraph |
| LLM Framework | LangChain |
| LLM Provider | Google Gemini (via `langchain-google-genai`) |
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | Next.js 16, React 19, Tailwind CSS 4 |
| Database | PostgreSQL (prod) / SQLite (dev) |
| Hosting | Railway (backend) · Vercel (frontend) |

## Project Structure

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry + CORS + health check
│   │   ├── config.py            # Pydantic settings
│   │   ├── dependencies.py      # LLM + DB dependency injection
│   │   ├── graph/
│   │   │   ├── state.py         # LangGraph state schema
│   │   │   ├── nodes.py         # Pipeline node functions
│   │   │   └── workflow.py      # Graph construction & compilation
│   │   ├── agents/
│   │   │   ├── clip_discovery_agent.py
│   │   │   ├── clip_validation_agent.py
│   │   │   └── editing_plan_agent.py
│   │   ├── services/
│   │   │   ├── transcript_service.py
│   │   │   └── chunking_service.py
│   │   └── api/
│   │       └── routes.py        # REST + SSE endpoints
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx         # Landing page
│   │   │   ├── result/page.tsx  # Results display
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   └── components/
│   │       └── url-input.tsx    # YouTube URL input + SSE client
│   ├── package.json
│   └── next.config.ts
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Google AI Studio API key

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:

```env
GOOGLE_API_KEY=your_google_ai_studio_key
DATABASE_URL=sqlite+aiosqlite:///./clipforge.db
SUPADATA_API_KEY=your_supadata_api_key  # Highly recommended for robust transcript fetching
YOUTUBE_PROXY=http://user:pass@proxy.com:8080 # Fallback proxy for youtube-transcript-api
```

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Create a `.env.local` file in `frontend/`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Open [http://localhost:3000](http://localhost:3000).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/process/stream` | SSE stream — real-time clip discovery |
| `POST` | `/api/v1/process` | Synchronous clip discovery |
| `GET` | `/docs` | Swagger UI |

## How It Works

1. **Input** — Paste a YouTube URL
2. **Transcript** — Fetches and cleans the transcript (filler word removal, segmentation)
3. **Discovery** — AI scans for viral hooks, counterintuitive takes, and high-energy moments
4. **Validation** — Clips validated against strict 40–60s rules (with retry loop)
5. **Editing Blueprint** — Frame-perfect editing plan generated per clip
6. **Output** — Real-time results streamed to the frontend via SSE

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Backend API | Railway | `clipforge-production-4a6f.up.railway.app` |
| Frontend | Vercel | `clipforge-eosin.vercel.app` |

### Environment Variables

**Backend (Railway):**
- `GOOGLE_API_KEY` — Google AI Studio API key
- `DATABASE_URL` — PostgreSQL connection string
- `SUPADATA_API_KEY` — Supadata API key for robust YouTube transcript fetching
- `YOUTUBE_PROXY` — Optional proxy for youtube-transcript-api fallback
- `PORT` — Set automatically by Railway

**Frontend (Vercel):**
- `NEXT_PUBLIC_API_URL` — Backend API URL

## License

Private — All rights reserved.
