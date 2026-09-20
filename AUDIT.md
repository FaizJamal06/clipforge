# ClipForge — Engineering & AI System Design Audit

**Scope:** full repository, read-only. **Method:** direct file reads + `git log`/`git ls-files` inspection across the backend (FastAPI/LangGraph), frontend (Next.js), and cross-cutting config/docs. Every claim below is cited to a file and line range from the current working tree unless explicitly marked "unconfirmed."

---

## 1. What the project does today

ClipForge takes a YouTube URL and returns AI-selected short-form clips ("hook + payoff" moments) with a structured editing blueprint (cut points, caption strategy, pacing, CTA), streamed to the browser as the pipeline runs.

**Stack:**

| Layer | Technology |
|---|---|
| Frontend | Next.js 16.1.6 (App Router), React 19.2.3, TypeScript (strict), Tailwind v4, shadcn primitives |
| Backend | FastAPI, Python 3.11, LangGraph 0.2+, LangChain 0.3+ |
| LLM | Google Gemini (`langchain-google-genai`), model `google/gemini-2.5-flash` |
| Transcript sourcing | Supadata API → `youtube-transcript-api` → YouTube InnerTube → YouTube Data API v3 (4-strategy fallback) |
| Data | SQLAlchemy 2.0 (async), SQLite locally, Postgres-capable via `asyncpg` |
| Deployment | Backend on Railway (`backend/Dockerfile`), frontend on Vercel |

**Data flow (high level):**

```mermaid
flowchart TD
    U[Browser] -- "GET /api/v1/process/stream (SSE)" --> API[FastAPI app<br/>backend/app/main.py]
    API --> MW[Middleware stack:<br/>SecurityHeaders → RateLimit → APIKey(no-op) → CORS<br/>backend/app/middleware.py, main.py:44-59]
    MW --> GRAPH[LangGraph pipeline<br/>backend/app/graph/workflow.py]

    subgraph GRAPH[LangGraph 7-node pipeline]
        N1[input_handler] --> N2[transcript_retrieval]
        N2 --> N3[transcript_processing]
        N3 --> N4[clip_discovery]
        N4 --> N5[clip_validation]
        N5 -- retry --> N4
        N5 -- continue --> N6[editing_plan]
        N6 --> N7[output_formatter]
    end

    N2 -->|4-strategy fallback| TS[transcript_service.py:<br/>Supadata → youtube-transcript-api →<br/>InnerTube → YouTube Data API]
    N4 -->|LLM call, structured output| LLM[Google Gemini<br/>via langchain-google-genai]
    N6 -->|LLM call, structured output| LLM
    N7 --> DB[(SQLite/Postgres<br/>processed_videos cache)]
    GRAPH --> API
    API -- SSE status events --> U
```

Two frontend routes: `/` (landing + waitlist signup) and `/result` (clip blueprint viewer). No authentication, no user accounts — every visitor shares one anonymous, global namespace.

---

## 2. AI system design review

### Prompt management — **Weak**

All prompts are hardcoded Python string literals passed to `ChatPromptTemplate.from_messages([...])`. No external template files, no versioning, no prompt registry, no A/B tracking.

- `backend/app/agents/clip_discovery_agent.py:43-78` — `CLIP_DISCOVERY_PROMPT`, transcript interpolated at lines 73-74.
- `backend/app/agents/clip_validation_agent.py:48-81` — `CLIP_VALIDATION_PROMPT` is defined but **never invoked**. `validate()` (`clip_validation_agent.py:167-241`) does purely programmatic checks and never calls an LLM chain, despite a docstring (lines 4-5) claiming "combination of programmatic checks and LLM-assisted analysis." This is dead/aspirational code.
- `backend/app/agents/editing_plan_agent.py:47-114` — `EDITING_PLAN_PROMPT`.

Prompt-injection sanitization is applied to interpolated content (`clip_discovery_agent.py:117`, `editing_plan_agent.py:137`) but not to the unused validation prompt, and the editing-plan prompt sanitizes the whole serialized JSON blob post-hoc rather than field-by-field (`editing_plan_agent.py:136-137`).

### Context handling — **Adequate**

Genuinely strong transcript acquisition, weaker downstream context management.

- **Transcript fetching**: a real 4-strategy fallback chain, `backend/app/services/transcript_service.py:564-661` — Supadata (510-561) → `youtube-transcript-api` (664-736, with proxy support) → YouTube InnerTube reverse-engineered API (373-503) → YouTube Data API v3 captions (165-370). Each failure is caught and logged with fallthrough; a friendly "IP banned" message surfaces if detected (651-656). This is the single best-engineered part of the codebase.
- **Chunking is wall-clock-duration-based, not token-based**: `chunking_service.py:120-177`, `chunk_duration=300.0s` with `overlap_duration=30.0s`. Discovery batches up to 7 chunks together (`BATCH_SIZE`, default 7, `config.py:61`), joined with a separator (`clip_discovery_agent.py:109-119`) — meaning a single LLM call can carry ~35 minutes of raw transcript text with **no token-count guard or truncation logic anywhere**.
- **Unbounded, unscoped cache**: `DISCOVERY_CACHE: dict[str, list[dict]] = {}` (`nodes.py:116`) is a module-level global, keyed only by `video_id`, no TTL, no size bound, no per-user isolation — two different callers requesting the same video share cached AI output, and the dict grows forever in a long-running process.
- No RAG/vector store/embeddings anywhere (confirmed via grep — zero matches for pinecone/weaviate/chroma/faiss/embedding). Not necessarily a gap for this use case (the whole transcript is short enough to pass directly), but worth noting since the project's own PRD (`clipforge_langgraph_prd.md:436-448`) floats it as a future item.
- `fetch_transcript_cached()` (`transcript_service.py:743-785`) implements Redis-based caching but is dead code — never called (`nodes.py:69` calls the uncached version directly).

### Tool use / agent loop design — **Adequate**

- Graph construction: `backend/app/graph/workflow.py:65-110`, 7 nodes (`workflow.py:74-80`), entry point `input_handler` (line 83), `check_status` conditional edges short-circuiting to `END` on failure (lines 29-33, wired at 86-89, 103).
- Real retry loop: `should_retry_validation` (lines 36-62) routes `clip_validation` back to `clip_discovery` up to `settings.max_validation_retries` (default 3, `config.py:53`).
- **No checkpointer** passed to `.compile()` (`workflow.py:106`) — no `MemorySaver`/persistence, so a graph run cannot be interrupted/resumed across process restarts.
- `transcript_retrieval` (`nodes.py:53-81`) calls `fetch_transcript` synchronously inside an `async def` node with no `asyncio.to_thread`/`run_in_executor` wrapping — a potential event-loop-blocking call under load.
- Retry math compounds: LangChain-level `max_retries=3` (`dependencies.py:65`) × agent-level manual retry loop (`for attempt in range(3)`, `clip_discovery_agent.py:127-156`, `editing_plan_agent.py:139-162`) × graph-level retry (3) = up to 27 possible LLM call attempts with 15s+ sleeps each, and **no overall request timeout** on the FastAPI route to bound this.
- `clip_validation` (`nodes.py:204-264`) **fails open**: on any exception it returns `validated_clips: candidate_clips` unvalidated (lines 257-264, comment calls this "graceful degradation") — meaning a crashed validator silently promotes unverified clips.

### Structured outputs & validation — **Strong**

Consistent use of Pydantic + LangChain's `.with_structured_output(...)` across every real LLM call site:

- `DiscoveredClip`/`ClipDiscoveryOutput` — `clip_discovery_agent.py:24-38`, invoked at line 103.
- `ValidationResult`/`ClipValidationOutput` — `clip_validation_agent.py:28-43` (schema defined, populated purely programmatically since the LLM path is dead — see above).
- `EditingSegment`/`ClipEditingPlan`/`EditingPlanOutput` — `editing_plan_agent.py:20-42`, invoked at line 125.
- API layer: `ProcessRequest`, `ProcessResponse`, `ClipResult`, `EditingPlanResult` — `backend/app/api/routes.py:32-80`.
- Waitlist input: `WaitlistRequest` with custom validators — `backend/app/api/waitlist.py:35-78`.

No LLM output reaches the client unvalidated at the schema level. The gap is *semantic* validation — nothing checks hook/payoff quality or virality-score plausibility; only duration and fuzzy transcript-containment are checked programmatically (`clip_validation_agent.py`).

### Guardrails — **Adequate**

- `PromptInjectionGuard` (`backend/app/security.py:20-121`) — regex pattern list (lines 20-48) for instruction-override/role-hijack/exfiltration/encoding markers, `sanitize()` (82-109) redacts matches and strips XML-like tags. This is **regex-based, not semantic** — bypassable by paraphrase, and it can also redact benign transcript content (e.g., a guest literally saying "act as a consultant"), corrupting the product's own verbatim-quote requirement.
- `InputSanitizer.sanitize_url()` (`security.py:141-180`) — length cap, character allowlist, scheme allowlist, and a domain allowlist restricted to `youtube.com`/`youtu.be` (172-175), applied at both API entry points (`routes.py:149,248`).
- `sanitize_error()` (`security.py:222-245`) strips file paths/tracebacks/memory addresses from error responses — used consistently (`routes.py:236,321`, `waitlist.py:163`).
- **Auth is a no-op by default**: `APIKeyMiddleware` (`middleware.py:130-161`) skips all checks if `settings.api_keys` is empty, which it is by default (`config.py:76`). The `/process` and `/process/stream` endpoints — which trigger billed LLM calls — are **completely unauthenticated** in the shipped default config, protected only by IP-based rate limiting.
- Rate limiting (`middleware.py:25-93`) is in-memory/per-process (`self._requests` dict), so it does not coordinate across multiple server replicas.
- Security headers (`middleware.py:100-119`) set correctly (X-Content-Type-Options, X-Frame-Options, HSTS when not debug) but no CSP.
- No output content-moderation/safety layer on any LLM-generated text before it reaches the client.

### Error handling — **Adequate**

- Transcript fetching: each of the 4 strategies individually try/excepted with logged fallthrough (`transcript_service.py:588-646`); aggregate error only if all 4 fail.
- LLM calls: distinguishes 429/quota (retried with backoff, `clip_discovery_agent.py:83-86,148`) from 402 billing errors (batch abandoned, lines 149-154) from other errors (abandoned immediately, no retry, lines 155-156) — but these failures are **logged and silently swallowed**, not surfaced to `state["errors"]`. A user can receive a "successful" response with fewer clips than expected and no explanation.
- Every node catches broad `Exception`, sets `status: "failed"`, and never lets exceptions propagate out of `.ainvoke()` — failure is communicated entirely through state fields, and the API maps this to **HTTP 200** with `status: "failed"` in the body (only truly unexpected exceptions produce a real 500, `routes.py:317-322`).
- Cache read/write errors are caught and logged as warnings without failing the request (`routes.py:172-173,222-224,270-271,311-313`) — reasonable, since cache is meant to be best-effort.

### Evaluation — **Missing**

No golden dataset, no quality metrics, no regression checks, no LLM-as-judge harness anywhere in the repo. `backend/benchmark_pipeline.py` measures timing only (and does so fragilely — see §3), not output quality.

### Observability — **Weak**

- Every module gets its own `logging.getLogger(__name__)` and logs consistently (13 files, grep-confirmed) — but **`logging.basicConfig()`/`dictConfig` is never called anywhere in the application** (confirmed via grep). Under plain `uvicorn app.main:app`, the root logger has no attached handler, meaning most `INFO`-level operational logs (rate-limiter waits, cache hits/misses, transcript-fetch fallbacks, discovery/validation progress) are likely **silently dropped** in production unless the hosting platform injects its own logging config. This is a concrete, fixable gap.
- No structured/JSON logs, no request/correlation IDs, no distributed tracing, no LangSmith (`LANGCHAIN_TRACING`/`LANGSMITH` — zero matches).
- No token/cost tracking anywhere — no `usage_metadata` capture, no per-request cost accounting.
- `GET /health` (`main.py:66-73`) returns a static payload with no dependency checks (DB/LLM reachability) — can't distinguish "process is up" from "pipeline is actually functional."

### Cost & latency optimization — **Weak**

- A DB-backed result cache exists (`processed_videos` table) with a real cache-poisoning bug fixed in commit `529c3c4` (previously, any cached entry — including ones saved with errors — was served as a hit; now reads check `errors` is empty and writes require a non-failed, error-free, video-id-bearing response — `routes.py:163-171,213,264-269,301-302`). **No TTL/invalidation exists** — a cached result is served forever regardless of upstream transcript changes, with no cache-busting endpoint.
- Redis is a listed dependency (`requirements.txt:30`) and fully configured in settings (`config.py:50`) but **entirely dead code** (`dependencies.get_redis()` returns `None` and is never called). This means the rate limiter, `DISCOVERY_CACHE`, and any future shared state are all in-process only — **they will not coordinate correctly if more than one uvicorn worker/replica runs**, a real correctness gap for horizontal scaling.
- No LLM token streaming to the client — SSE only streams graph-state transitions (`routes.py:194`, `stream_mode="values"`), not token-by-token model output.
- No model routing/tiering (e.g., cheaper model for discovery, better model for final ranking) — one model for everything.

---

## 3. General engineering weaknesses

**Secrets & credential hygiene**
- A live Supadata API key is hardcoded in plaintext in `test_supadata.py:5`. **Correction from an earlier pass of this audit**: `git log --all -- test_supadata.py` and `git ls-files` confirm this file has **never been committed** — it's untracked, sitting only in the local working directory, so it is not in git history. It is still a real credential sitting in plaintext in a script that matches the live key currently configured in `backend/.env`, so it should still be rotated as a precaution and the script should read the key from the environment instead — but this is a working-tree hygiene issue, not a git-history leak.
- `backend/.env` itself is correctly gitignored (confirmed via `git ls-files` — not tracked); the root `.gitignore:14` bare `.env` rule covers it. Good practice there.
- `.env.example` is out of date relative to the real settings schema — missing `YOUTUBE_API_KEY`, `YOUTUBE_PROXY`, `SUPADATA_API_KEY`, `LLM_RATE_LIMIT_RPM`, `LLM_BATCH_SIZE`, all of which the code actually reads (`config.py:59-61,71-73`).

**Config truthfulness**
- `config.py:21-23,42-46` documents the provider as "LLM Provider (OpenRouter)" and sets `llm_base_url = "https://openrouter.ai/api/v1"`, but `dependencies.py` hardwires `ChatGoogleGenerativeAI` and **never reads `llm_base_url` at all** (grep-confirmed). The settings model actively misrepresents which provider is being called.
- The configured **default** model string `google/gemini-2.5-flash` (`config.py:44`) uses an OpenRouter-style slug prefix, which `ChatGoogleGenerativeAI` does not expect (it wants native Gemini IDs like `gemini-2.5-flash`). In practice this default is masked because the real `backend/.env` overrides it with the correct `gemini-2.5-flash` — but the wrong default is still worth fixing since anyone bootstrapping from `.env.example`/the README without setting `LLM_MODEL` explicitly would hit it.
- README setup instructions (`README.md:123-130`) tell developers to set `GOOGLE_API_KEY`, but the code reads `LLM_API_KEY` (`config.py:43`) — following the README literally silently misconfigures the LLM client.
- **Addendum found while implementing Phase 1**: `config.py`'s `database_url`/`redis_url` Pydantic fields are never read anywhere (grep-confirmed). `backend/app/database.py` instead calls `os.getenv("DATABASE_URL", DEFAULT_DB_URL)` directly, and nothing in the app ever calls `load_dotenv()` to populate real process environment variables from `backend/.env`. In practice this means `backend/.env`'s `DATABASE_URL`/`REDIS_URL` values have **zero effect locally** — `database.py` always falls back to local SQLite in dev regardless of what's set there, only picking up `DATABASE_URL` when it's a real OS-level env var (as it would be on Railway). This is the same class of bug as the `llm_base_url` issue above — two different env-loading mechanisms (pydantic-settings' own `.env` parsing vs. raw `os.getenv`) silently disagree. Worth consolidating onto one settings source when Postgres is wired up for real in the roadmap's Phase 2.

**Repository hygiene**
- `backend/data/clipforge.db` is **tracked in git** (committed in `f1aa2fa`) and currently shows as `modified` in `git status` — a live, churning SQLite file with real cached data (2 rows of actual AI output inspected directly) is versioned in source control. No `*.db` rule exists in the root `.gitignore`; `backend/.dockerignore` only excludes it from the *Docker build context*, a different mechanism from git tracking.
- Debug/manual scripts are committed alongside production code rather than isolated: `backend/debug_yt.py` (169 lines, hardcoded test video ID), `backend/benchmark_pipeline.py` (191 lines, fragile — infers stage timing by grepping log text for an internal SDK string, `benchmark_pipeline.py:111`), `backend/test_pipeline.py` (51 lines) — the last of these is **stale/broken**: it calls `getattr(clip, 'title', None)` etc. on plain `dict`s (`test_pipeline.py:37-44`), which always returns the default, so its diagnostic output silently shows nothing useful even on success.
- `test_supadata.py` (repo root, untracked... actually tracked — see secrets note above) sits outside both `backend/` and `tests/`, is not pytest-collected, and would hit the real Supadata API if run directly.
- Root `Dockerfile` duplicates `backend/Dockerfile` almost line-for-line; git history (`chore: bust Docker cache in backend Dockerfile (Railway uses this one)`) confirms only `backend/Dockerfile` is actually used — the root one is dead/leftover from an earlier deployment attempt.
- No root-level `.dockerignore` — if the root `Dockerfile` were ever built with repo-root context, `backend/.env` and `clipforge.db` would be copied into the image (the root Dockerfile appears unused in practice, but this is latent risk if someone resurrects it).

**Dead dependencies**
- `langchain-openai>=0.2.0` (`requirements.txt:13`) — never imported anywhere (grep-confirmed).
- `redis>=5.2.0` (`requirements.txt:30`) — never used (see Cost & latency section above).
- `alembic>=1.14.0` (`requirements.txt`) — no `alembic/` directory or `alembic.ini` exists anywhere; the app instead calls `Base.metadata.create_all` at startup (`main.py:24-25`), meaning schema changes have no migration path today.
- `requirements.txt` lists `asyncpg` twice at two different version pins (harmless but sloppy).

**No user/account model**
- No `users` table anywhere. The only identity concept in the entire system is IP address (used for rate limiting and waitlist abuse tracking). `processed_videos` is a single global cache namespace shared by every caller — there is no per-user data isolation at all today.

**No CI**
- No `.github/workflows/` directory exists — confirmed absent at the top level (an exhaustive recursive search of every hidden directory was not performed, so treat "no CI at all" as highly likely but not 100% proven). The 88-test `tests/` suite exists but nothing appears to run it automatically on push/PR.

**Documentation drift**
- `docs/LANGGRAPH_PIPELINE.md:118` describes editing-plan output as an unstructured `raw_plan` string, but the real implementation uses a fully structured `ClipEditingPlan` Pydantic model (`editing_plan_agent.py:20-42`) — the doc predates that change and was never updated.
- `docs/LANGGRAPH_PIPELINE.md` also describes transcript retrieval as using only `youtube-transcript-api`, predating the 4-layer Supadata-led fallback chain that shipped later.
- `clipforge_langgraph_prd.md` (553 lines) and `.planning/PROJECT.md` describe a design that was never built as specified: Claude models (PRD recommends this; code uses Gemini only), Streamlit frontend (PROJECT.md; shipped as Next.js), Redis+Postgres caching (PRD; Redis is dead code), and an optional vector DB (never implemented). These read as pre-code planning artifacts, not living documentation — useful for context but actively misleading if read as current-state docs.
- Both are explicitly AI-generated/AI-assisted planning documents per their own content and per `AI_INSIGHTS.md`'s framing.

**Licensing**
- README.md:181 states "License: Private — All rights reserved," but **no LICENSE file exists** anywhere in the repo — the claim has no legal backing document.

**Frontend gaps**
- Zero tests of any kind (no test runner in `package.json`, no `*.test.*`/`*.spec.*` files under `src`).
- No authentication (a "Log in" link exists on the landing page, `src/app/page.tsx:115-117`, but it's a dead `href="#"` anchor with no backing flow).
- No Next.js route-level `error.tsx`/`loading.tsx` — no error boundaries, no route-level loading skeletons anywhere in `src/app`.
- The SSE `EventSource` created in `url-input.tsx:37-70` has no cleanup registered on component unmount (`useEffect` cleanup absent) — a connection-leak risk if a user navigates away mid-stream. Its `onerror` handler (lines 65-70) is a blanket handler that can't distinguish a normal stream-close from a real network failure.
- `NEXT_PUBLIC_API_URL` with the same hardcoded `localhost:8000` fallback is duplicated across three files (`url-input.tsx:8-9`, `waitlist-form.tsx:5`, `result/page.tsx:6`) rather than centralized.
- Styling is set up with shadcn/Tailwind but barely used in practice — most UI is large inline `style={{}}` objects plus a 1342-line hand-written `globals.css`, so the design-system investment isn't paying off structurally.

---

## 4. What's already strong — worth keeping and highlighting

- **The 4-layer transcript fallback chain** (`transcript_service.py:564-661`) is genuinely well-engineered resilience work — most portfolio projects don't attempt this level of defense against a flaky external dependency.
- **Consistent structured-output discipline**: every real LLM call site uses Pydantic + `with_structured_output`, with no ad-hoc JSON parsing of model output anywhere. This is the single strongest AI-system-design property in the codebase and worth calling out explicitly to a reviewer.
- **A real, working adaptive rate limiter** (`rate_limiter.py:20-107`) plus layered retry/backoff for 429s with actual `RESOURCE_EXHAUSTED`/`retry-after` parsing (`clip_discovery_agent.py:83-86`) — shows real production-mindedness even though it doesn't yet coordinate across replicas.
- **A security-conscious middleware stack** (headers, rate limiting, input sanitization, error message sanitization, a prompt-injection guard) that goes further than most solo-built AI apps attempt, even where individual pieces (the injection regex) have known limits.
- **A real, fixed production bug with a clear before/after**: the cache-poisoning fix in commit `529c3c4` is a genuinely good story for an interview — a subtle correctness bug (poisoned cache serving failed/partial results forever) found and fixed with an explicit read/write guard.
- **A strong root README** (`README.md`) — live links, an architecture diagram (ASCII), a tech-stack table, specific engineering-highlight claims, setup instructions, and an API table. This is meaningfully better than a typical solo-project README and a good foundation to build the roadmap's documentation work on.
- **Reasonable existing test coverage for a solo project**: 88 passing tests including a real `httpx`/ASGI integration suite (`tests/test_today.py`) that overrides the DB dependency with in-memory SQLite and exercises real request/response paths, plus targeted unit tests for the trickiest programmatic logic (transcript containment matching, chunking).
- **The waitlist feature's abuse-prevention design** (`backend/app/api/waitlist.py`) — honeypot field, disposable-domain blocklist, duplicate-signup handling that avoids user enumeration, IP/User-Agent capture for abuse tracking — is thoughtful, appropriately-scoped security work for what could have been a throwaway feature.

---

## Notes on confidence

A few items above are flagged explicitly as unconfirmed rather than guessed:
- Whether CI truly does not exist anywhere (no `.github/workflows` found at top level; not exhaustively verified against every possible hidden CI config).
- Whether the `google/gemini-2.5-flash` model string actually errors or is silently tolerated by the installed `langchain-google-genai` version (static read only, not executed).
- Whether production (Railway) currently runs with `DEBUG=true` (would explain the public `/docs` link the README advertises) — this depends on platform env vars not visible in this local checkout.
