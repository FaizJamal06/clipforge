# Research Summary — ClipForge AI

## Stack Decision

**Python 3.11+ / FastAPI / LangGraph / LangChain / OpenRouter / Streamlit / PostgreSQL / Redis**

- LangGraph for stateful multi-node pipeline with conditional loops (validation retry)
- OpenRouter via `langchain-openrouter` for model flexibility — start with a strong reasoning model (Claude Sonnet 4 or Gemini 2.5 Pro)
- FastAPI for async API layer with Pydantic validation
- Streamlit for rapid prototyping UI
- PostgreSQL for persistence, Redis for caching
- Docker Compose for local development (all services in one command)

## Table Stakes Features (v1)

1. YouTube URL input → transcript extraction → cleaning → chunking
2. AI clip discovery — viral moment detection with hook/payoff structure
3. Top 3 clips, 40–60 seconds each, verbatim from transcript
4. Validation pipeline — containment, continuity, duration, hallucination checks
5. Retry loop (max 3) — re-generate on validation failure
6. Editing plan per clip — timestamps, B-roll, captions, pacing
7. Structured output display via Streamlit

## Key Architecture Insight

The pipeline is a **linear graph with one conditional loop**:

```
Input → Transcript → Processing → Clip Discovery → Validation ─┐
                                        ↑                       │
                                        └── retry (max 3) ──────┘
                                                                 │
                                                                 ▼
                                                         Editing Plan → Output
```

State is managed via a `TypedDict` passed between nodes. Each node reads and updates shared state.

## Top 3 Pitfalls to Watch

1. **LLM Hallucination** — Clips must be verbatim. Validate with exact substring matching. Prompt must explicitly instruct "copy EXACTLY."
2. **youtube-transcript-api fragility** — Unofficial library. Wrap in abstraction layer, cache transcripts, handle errors gracefully.
3. **Context window overflow** — Long podcasts exceed LLM limits. Must chunk transcripts and use a two-stage candidate selection.

## Build Order Recommendation

| Order | Component | Dependency |
|-------|-----------|------------|
| 1 | Project scaffolding + Docker | None |
| 2 | Data models (Pydantic + DB) | Scaffolding |
| 3 | Transcript pipeline | Data models |
| 4 | LangGraph pipeline skeleton | Data models |
| 5 | LLM integration (OpenRouter) | LangGraph |
| 6 | Clip Discovery + Validation | LLM + Transcript |
| 7 | Editing Plan generation | Validation |
| 8 | FastAPI endpoints | Pipeline |
| 9 | Database integration | FastAPI |
| 10 | Streamlit UI | API endpoints |
| 11 | Testing + polish | All |

---
*Synthesized: 2026-03-11*
