# Stack Research — ClipForge AI

## Recommended 2025 Stack

### AI Orchestration
| Component | Choice | Version | Confidence | Rationale |
|-----------|--------|---------|------------|-----------|
| Orchestration | **LangGraph** | latest | ✅ High | Stateful directed graphs, conditional branching, validation loops, checkpointing. Used by Uber, LinkedIn, Replit in production. |
| LLM Framework | **LangChain** | latest | ✅ High | Prompt templates, tool interfaces, LLM wrappers. LangGraph integrates directly. |
| LLM Provider | **OpenRouter** | — | ✅ High | Unified API for multiple models. `langchain-openrouter` package available. |
| Reasoning Model | **anthropic/claude-sonnet-4** or **google/gemini-2.5-pro** | — | ✅ High | Strong reasoning, large context windows, good for transcript analysis. |

### Backend
| Component | Choice | Version | Confidence | Rationale |
|-----------|--------|---------|------------|-----------|
| Language | **Python 3.11+** | 3.11+ | ✅ High | AI ecosystem standard, LangGraph/LangChain native. |
| API Framework | **FastAPI** | latest | ✅ High | Async-native, auto OpenAPI docs, Pydantic validation. |
| Database | **PostgreSQL** | 16+ | ✅ High | Reliable, JSONB for flexible state storage. |
| Caching | **Redis** | 7+ | ✅ High | Transcript caching, pipeline state, rate limiting. |
| Transcript API | **youtube-transcript-api** | latest | ⚠️ Medium | Free, no API key. Risk: unofficial, YouTube can break it. |

### Frontend
| Component | Choice | Version | Confidence | Rationale |
|-----------|--------|---------|------------|-----------|
| UI | **Streamlit** | latest | ✅ High | Rapid prototyping, built-in loading states, Python-native. |

### Infrastructure
| Component | Choice | Confidence | Rationale |
|-----------|--------|------------|-----------|
| Containerization | **Docker + docker-compose** | ✅ High | Postgres + Redis + backend in one command. |
| Package Management | **Poetry** or **uv** | ✅ High | Dependency lock files, reproducible builds. |

## What NOT to Use (v1)
- **Next.js/React** — Overkill for v1. Streamlit is faster to iterate.
- **Vector databases** (Pinecone/Weaviate/Chroma) — Transcript chunking is sufficient; semantic retrieval adds complexity without proven value for this use case.
- **LangSmith** — Nice for observability but not required for v1; add later.
- **Celery/task queues** — FastAPI async + Redis is sufficient for single-user throughput.

---
*Researched: 2026-03-11*
