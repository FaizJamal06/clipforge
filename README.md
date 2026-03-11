# ClipForge AI 🎙️✂️

> AI-powered podcast clipping system that identifies viral 40–60 second clips and generates professional editing blueprints.

Built with a modern 2025 generative AI stack — **LangGraph** for agentic orchestration, **LangChain** for LLM interactions, **FastAPI** for the backend, and **Next.js** for the frontend.

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐     ┌───────────┐
│   Next.js    │────▶│              FastAPI Backend                 │────▶│ PostgreSQL│
│   Frontend   │◀────│                                              │◀────│   Redis   │
└─────────────┘     │  ┌──────────────────────────────────────┐    │     └───────────┘
                    │  │       LangGraph Pipeline              │    │
                    │  │                                        │    │
                    │  │  Input → Transcript → Processing →    │    │
                    │  │  Clip Discovery → Validation →        │    │
                    │  │  Editing Plan → Output Formatter      │    │
                    │  │         ↑              |               │    │
                    │  │         └── retry ─────┘               │    │
                    │  └──────────────────────────────────────┘    │
                    │                    │                          │
                    │                    ▼                          │
                    │            ┌──────────────┐                  │
                    │            │  OpenRouter   │                  │
                    │            │  (LLM API)   │                  │
                    │            └──────────────┘                  │
                    └──────────────────────────────────────────────┘
```

## Project Structure

```
clipforge/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── dependencies.py      # Dependency injection
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
│   │       └── routes.py        # REST endpoints
│   └── requirements.txt
├── frontend/                    # Next.js + React + Tailwind + shadcn/ui
├── tests/
├── .env.example
├── .gitignore
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Orchestration | LangGraph |
| LLM Framework | LangChain |
| LLM Provider | OpenRouter |
| Backend | Python, FastAPI |
| Frontend | Next.js, React, Tailwind, shadcn/ui |
| Database | PostgreSQL |
| Cache | Redis |

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Redis

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env  # Edit with your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/v1/process` | Submit YouTube URL for clip discovery |
| `GET` | `/api/v1/status/{job_id}` | Check processing status |

## How It Works

1. **Input** — User pastes a YouTube URL
2. **Transcript** — System fetches and processes the transcript
3. **Discovery** — AI analyzes transcript for viral moments
4. **Validation** — Clips are validated against strict rules (with retry loop)
5. **Editing Plan** — Professional editing blueprint generated per clip
6. **Output** — Structured results returned to the frontend

## Current Status

🏗️ **Architecture Scaffold Complete** — Project structure, LangGraph workflow, and placeholder agents are in place. Full agent implementations are the next development phase.

## License

Private — All rights reserved.
