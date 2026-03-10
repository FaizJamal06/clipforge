# ClipForge AI

## What This Is

ClipForge AI is a production-grade AI system that automatically identifies the top 3 viral short-form clips (40–60 seconds each) from long-form podcast content and generates professional editing blueprints for video editors. Users paste a YouTube URL and receive verbatim clip scripts, B-roll suggestions, caption strategies, and short-form pacing instructions — reducing clip discovery from hours to seconds.

Built using a modern 2025 generative AI stack orchestrated through LangGraph, this project demonstrates industrial-grade AI systems engineering: agentic workflows, validation pipelines, tool integration, and production evaluation loops.

## Core Value

Accurately identify verbatim viral segments from podcast transcripts — the clips must exist in the original transcript, be continuous, and contain a hook + payoff structure.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Accept YouTube URL and extract video ID with validation
- [ ] Fetch full transcript with timestamps via youtube-transcript-api
- [ ] Clean, merge speaker segments, and chunk transcript preserving timestamps
- [ ] AI-powered clip discovery: analyze transcript for viral storytelling, emotional peaks, curiosity gaps
- [ ] Select top 3 viral clips (40–60 seconds each, verbatim, continuous, hook + payoff)
- [ ] Validate each clip: exists in transcript, continuous, correct length, no hallucination
- [ ] Validation retry loop (max 3 retries) — re-run clip discovery on failure
- [ ] Generate editing plan per clip: timestamps, B-roll ideas, captions, pacing instructions
- [ ] Format and present structured output (clip script + editing plan)
- [ ] Streamlit UI for user input and output display
- [ ] FastAPI backend serving the LangGraph pipeline
- [ ] PostgreSQL for storing transcripts, clips, and job history
- [ ] Redis for caching transcripts and pipeline state
- [ ] OpenRouter integration for LLM calls (strong reasoning model)
- [ ] Clean, production-grade code architecture

### Out of Scope

- Multi-language transcripts — English only for v1
- Next.js/React frontend — Streamlit first, upgrade later
- Automatic video clipping (FFmpeg) — future roadmap
- AI B-roll generation (Runway/Pika) — future roadmap
- Virality scoring model — future roadmap
- Vector database / semantic retrieval — defer unless transcripts are very large
- Vercel/Railway deployment — will deploy later, not part of initial build
- OAuth / user authentication — not needed for v1

## Context

- **Domain**: Podcast editors spend 1–3 hours per episode finding viral moments manually. This tool automates that to <10 seconds.
- **Target users**: Podcast editors, content agencies, social media growth teams, YouTube clip channels, TikTok/Reels editors
- **Portfolio project**: Designed to demonstrate AI engineering competency — clean architecture, agentic patterns, production reliability
- **Prior work**: PRD document (`clipforge_langgraph_prd.md`) defines the full vision; this project starts with the AI pipeline core

## Constraints

- **LLM Provider**: OpenRouter — keys to be provided later, architecture must support provider swapping
- **Language**: Python for backend/AI pipeline
- **Orchestration**: LangGraph (integrated with LangChain)
- **Frontend**: Streamlit for v1 (simple, fast to iterate)
- **API**: FastAPI for the backend API layer
- **Database**: PostgreSQL (persistence) + Redis (caching)
- **Transcript Source**: YouTube URLs only via `youtube-transcript-api`
- **Clip Count**: Top 3 clips per run
- **Clip Length**: 40–60 seconds each
- **Validation Retries**: Max 3 per clip
- **Language Support**: English only

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| OpenRouter for LLM | Flexibility to switch models; strong reasoning model needed | — Pending |
| Streamlit over Next.js for v1 | Focus on AI pipeline first, iterate faster | — Pending |
| Top 3 clips instead of single best | More value per run, demonstrates ranking capability | — Pending |
| PostgreSQL + Redis included in v1 | Production-grade persistence needed even for portfolio | — Pending |
| LangGraph orchestration | Multi-node stateful pipeline with validation loops requires proper orchestration | — Pending |
| youtube-transcript-api | Simple, free, no API key needed for transcripts | — Pending |

---
*Last updated: 2026-03-11 after initialization*
