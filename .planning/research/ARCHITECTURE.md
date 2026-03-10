# Architecture Research — ClipForge AI

## System Components

### 1. API Layer (FastAPI)
- REST endpoints for submitting URLs and retrieving results
- Request validation (Pydantic models)
- Async processing support
- Health check / status endpoints

### 2. LangGraph Pipeline (Core)
- Stateful directed graph with shared state object
- 6 nodes in sequence with one conditional loop

### 3. Data Layer
- PostgreSQL: transcripts, clips, job history, editing plans
- Redis: transcript cache, pipeline state, rate limiting

### 4. UI Layer (Streamlit)
- Input form (YouTube URL)
- Processing status / progress indicators
- Results display (clip scripts + editing plans)
- Copy-to-clipboard functionality

## Component Boundaries

```
┌─────────────┐     ┌──────────────────────────────────────────────┐     ┌───────────┐
│  Streamlit   │────▶│              FastAPI Backend                 │────▶│ PostgreSQL│
│     UI       │◀────│                                              │◀────│   Redis   │
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

## Data Flow

1. **User** → Streamlit → FastAPI: YouTube URL
2. **FastAPI** → LangGraph: Initiate pipeline
3. **Input Node**: Validate URL, extract video ID
4. **Transcript Node**: youtube-transcript-api → fetch transcript → cache in Redis → store in Postgres
5. **Processing Node**: Clean, merge, chunk transcript (preserve timestamps)
6. **Clip Discovery Node**: Send chunks to LLM via OpenRouter → analyze for viral moments → return top 3 candidates
7. **Validation Node**: Check each clip against rules → if fail, loop back (max 3 retries)
8. **Editing Plan Node**: Send validated clips to LLM → generate editing blueprint per clip
9. **Output Node**: Format structured response → store in Postgres → return to API
10. **FastAPI** → Streamlit: Structured results

## LangGraph State Schema

```python
class ClipForgeState(TypedDict):
    youtube_url: str
    video_id: str
    transcript: list[dict]           # raw transcript segments
    transcript_chunks: list[str]     # processed chunks
    candidate_clips: list[dict]      # top 3 candidates
    validated_clips: list[dict]      # clips that passed validation
    failed_clips: list[dict]         # clips that failed validation
    editing_plans: list[dict]        # editing plan per clip
    retry_count: int                 # validation retry counter
    errors: list[str]                # error log
    status: str                      # pipeline status
```

## Suggested Build Order

1. **Project scaffolding** — Directory structure, dependencies, Docker setup
2. **Data models** — Pydantic schemas, database models
3. **Transcript pipeline** — URL validation + transcript fetching + processing
4. **LangGraph pipeline** — Node implementations, state management
5. **LLM integration** — OpenRouter + prompt engineering
6. **Validation loop** — Clip validation with retry logic
7. **Editing plan generation** — Second LLM call
8. **FastAPI endpoints** — Wire pipeline to API
9. **Database integration** — Postgres + Redis
10. **Streamlit UI** — Input form + results display
11. **Testing + polish** — End-to-end tests, error handling

---
*Researched: 2026-03-11*
