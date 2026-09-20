# ClipForge AI ⚡

> AI-powered podcast clipping that identifies viral 40–60 second moments and generates frame-perfect editing blueprints — in seconds.

**[Live App](https://clipforge-eosin.vercel.app)** · **[API Health](https://clipforge-production-4a6f.up.railway.app/health)** · **[API Docs](https://clipforge-production-4a6f.up.railway.app/docs)**

---

## The Vision
ClipForge AI is a production-grade AI system that automatically identifies viral short‑form clips from long-form podcast content and generates a professional editing blueprint for video editors. Built on a modern generative AI stack, the system is orchestrated through **LangGraph** to simulate real-world production AI workflows.

It reduces the typical 1-3 hours of manual podcast clip discovery to **under 10 seconds**.

## Architecture

ClipForge AI leverages a state-machine based multi-agent architecture via LangGraph. 

```
┌─────────────┐     ┌──────────────────────────────────────────────┐     ┌───────────┐
│   Next.js   │────▶│              FastAPI Backend                 │────▶│ PostgreSQL│
│   Frontend  │◀────│                                              │◀────│   (Prod)  │
│   (Vercel)  │ SSE │  ┌──────────────────────────────────────┐    │     └───────────┘
│             │     │  │       LangGraph Pipeline             │    │
│             │     │  │                                      │    │
│             │     │  │  Input → Transcript → Processing →   │    │
│             │     │  │  Clip Discovery Agent → Validation → │    │
│             │     │  │  Editing Plan Agent → Formatter      │    │
│             │     │  │         ↑              |             │    │
│             │     │  │         └── retry ─────┘             │    │
│             │     │  └──────────────────────────────────────┘    │
│             │     │                    │                         │
│             │     │                    ▼                         │
│             │     │            ┌──────────────┐                  │
│             │     │            │ Google Gemini│                  │
│             │     │            │  (Direct API)│                  │
│             │     │            └──────────────┘                  │
└─────────────┘     └──────────────────────────────────────────────┘
    Vercel                         Railway
```

## Key Engineering Highlights

ClipForge goes beyond a standard AI wrapper by implementing robust, production-ready engineering patterns:

- **4-Layer Transcript Fallback Pipeline**: To combat YouTube IP bans, the system attempts a waterfall approach: Supadata API (primary) → `youtube-transcript-api` (with proxy) → InnerTube API → YouTube Data API v3. This ensures near-100% reliability for transcript fetching.
- **Adaptive Rate Limiter**: A custom sliding-window rate limiter prevents the agents from exceeding Gemini's free-tier limits (5 requests per minute), sharing a global quota pool dynamically across agents, adapting with exponential back-off on 429s.
- **First-Class Security & Prompt Injection Guards**: User transcripts can contain malicious commands. The `security.py` module uses regex-based prompt injection detection, input sanitization, and strict XML-delimited prompts to protect the LLM.
- **Fuzzy Output Validation**: Strict LLM output validation (requiring a 100% exact substring match) often fails in reality. The Validation Agent employs a fuzzy matching strategy (0.50 threshold) and a sliding window comparison to balance prompt adherence with real-world LLM variations.
- **Cache Poisoning Prevention**: Results are cached in the database for instant subsequent retrievals, with explicit guardrails to prevent caching of failed runs or errors.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI Orchestration** | LangGraph |
| **LLM Framework** | LangChain |
| **LLM Provider** | Google Gemini (via `langchain-google-genai`) |
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 4 |
| **Database** | PostgreSQL (prod) / SQLite (dev) |
| **Deployment** | Railway (backend) · Vercel (frontend) |

## Project Structure

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry + CORS + health check
│   │   ├── config.py            # Pydantic settings
│   │   ├── dependencies.py      # LLM + DB dependency injection
│   │   ├── middleware.py        # Middleware
│   │   ├── rate_limiter.py      # Sliding-window adaptive rate limiter
│   │   ├── security.py          # PromptInjectionGuard & input sanitization
│   │   ├── graph/
│   │   │   ├── state.py         # LangGraph state schema
│   │   │   ├── nodes.py         # Pipeline node functions
│   │   │   └── workflow.py      # Graph construction & compilation
│   │   ├── agents/
│   │   │   ├── clip_discovery_agent.py   # Analyzes transcript for viral moments
│   │   │   ├── clip_validation_agent.py  # Fuzzy logic verbatim validation loop
│   │   │   └── editing_plan_agent.py     # Generates blueprint (b-roll, captions)
│   │   ├── services/
│   │   │   ├── transcript_service.py     # 4-layer fallback transcript fetcher
│   │   │   └── chunking_service.py       # Preserves timestamps during LLM chunking
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
├── AI_INSIGHTS.md               # Detailed AI development journey & case studies
├── clipforge_langgraph_prd.md   # Original Product Requirements Document
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

Create a `.env` file in `backend/` (see `.env.example` at the repo root for the full list of settings):

```env
LLM_API_KEY=your_google_ai_studio_key
LLM_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite+aiosqlite:///./data/clipforge.db
SUPADATA_API_KEY=your_supadata_api_key  # Highly recommended for robust transcript fetching
YOUTUBE_PROXY=http://user:pass@proxy.com:8080 # Fallback proxy for youtube-transcript-api
```

Start the dev server:
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

## The AI Pipeline (How It Works)

1. **Input & Sanitization**: URL is ingested and sanitized against prompt injections via `security.py`.
2. **Transcript Retrieval**: The `transcript_service` fetches and cleans the transcript (filler word removal, segmentation) using a multi-strategy fallback.
3. **Chunking**: Transcripts are chunked appropriately for the LLM context window while preserving critical timestamp associations.
4. **Discovery (LangGraph Node)**: `clip_discovery_agent` AI scans for viral hooks, counterintuitive takes, and high-energy moments.
5. **Validation (LangGraph Node)**: `clip_validation_agent` ensures the clip matches the transcript continuously for 40-60s using a fuzzy matcher. Fails trigger a cyclic graph loop for retry.
6. **Editing Blueprint (LangGraph Node)**: `editing_plan_agent` generates a frame-perfect editing plan, suggesting pacing, captions, and b-roll.
7. **Output**: Fast real-time results streamed to the frontend via Server-Sent Events (SSE), cleanly cached to avoid duplicate API work.

## Deployment

| Service | Platform | URL |
|---------|----------|-----|
| Backend API | Railway | `clipforge-production-4a6f.up.railway.app` |
| Frontend | Vercel | `clipforge-eosin.vercel.app` |

## License

Private — All rights reserved.
