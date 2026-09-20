# ClipForge — Roadmap to Portfolio-Grade SaaS

This roadmap turns the findings in [AUDIT.md](./AUDIT.md) into a phased, reviewable implementation plan. It assumes the existing stack (Next.js + FastAPI/LangGraph + SQLAlchemy) stays — nothing here justifies a framework rewrite. Each phase is meant to ship as its own branch/commit series, with tests run and behavior verified before moving to the next.

**Recommended stack additions** (rationale inline per phase): Auth.js (NextAuth v5) for Google OAuth, Postgres (path already exists in `database.py`), Alembic for migrations (already a dependency, currently unused), Redis (already a dependency, currently unused) for shared rate-limiting/cache, `arq` for a lightweight async job queue, GitHub Actions for CI.

---

## Phase 0 — Immediate hygiene (do first, independent of everything else)

**Why:** These are correctness/security issues, not design debate — they should be fixed regardless of which direction the rest of the roadmap goes.

| Item | Why it matters | Files | Effort |
|---|---|---|---|
| Rotate the Supadata key and remove it from `test_supadata.py` | A real API key sits hardcoded in plaintext (`test_supadata.py:5`) — untracked in git, but still a credential on disk that should read from env instead | `test_supadata.py` | S |
| Untrack `backend/data/clipforge.db` from git, add `*.db` to `.gitignore` | Live churning binary file in source control | `.gitignore`, `backend/data/clipforge.db` | S |
| Fix `config.py` to stop claiming OpenRouter when the code hardwires Gemini; remove unused `llm_base_url` or actually wire it up | Config should describe reality — this is the kind of inconsistency a reviewer will notice immediately | `backend/app/config.py`, `backend/app/dependencies.py` | S |
| Remove dead dependencies (`langchain-openai`, unused `alembic`/`redis` *or* actually wire them up in later phases) | Dead deps signal incomplete follow-through | `backend/requirements.txt` | S |
| Fix README env var drift (`GOOGLE_API_KEY` → `LLM_API_KEY`), update `.env.example` to match real settings schema | Following the README today silently misconfigures the app | `README.md`, `.env.example` | S |
| Add `logging.basicConfig()` (or a small structured-logging setup) so existing `logger.*` calls actually reach stdout | Currently most operational logs are likely silently dropped in production | `backend/app/main.py` | S |
| Move `debug_yt.py`, `benchmark_pipeline.py`, `test_pipeline.py` into a `backend/scripts/` directory (or delete `test_pipeline.py`, which is stale/broken) | Keeps ad-hoc scripts visibly separate from production code | `backend/*.py` → `backend/scripts/` | S |
| Add a LICENSE file matching the README's stated "Private — All rights reserved" | Currently unbacked claim | new `LICENSE` | S |

**Dependencies:** none — can be done in parallel with everything else, ideally first.

---

## Phase 1 — Auth & per-user data isolation

**Why it matters:** This is the single biggest gap between "demo" and "SaaS." Nothing today distinguishes one user from another; `processed_videos` is a shared global cache; the AI endpoints are unauthenticated by default.

**Approach:** Google OAuth via **Auth.js (NextAuth v5)** in the Next.js frontend. Auth.js handles the OAuth dance and issues a session; the frontend attaches a signed JWT (Auth.js can mint one, or the backend can issue its own after verifying the Google ID token once) as a `Bearer` token on every API call. FastAPI verifies the JWT signature (shared secret, or JWKS if using Google's ID token directly) on every protected route via a dependency.

*Why not backend-driven OAuth (e.g., Authlib in FastAPI issuing cookies)?* The frontend (Vercel) and backend (Railway) are different origins, so cookie-based sessions would need `SameSite=None; Secure` cross-domain cookies — more moving parts than a stateless Bearer JWT, and harder to explain cleanly in an interview. Auth.js on the frontend is the more standard pattern for this split-deployment shape.

| Item | Why | Files | Effort | Depends on |
|---|---|---|---|---|
| Add Auth.js with Google provider to frontend | Standard, well-documented OAuth flow | new `frontend/src/app/api/auth/[...nextauth]/route.ts`, `frontend/src/lib/auth.ts` | M | — |
| Add `users` table | Real identity to scope data by | new `backend/app/models/user.py` | S | — |
| Add JWT verification dependency for FastAPI routes | Every route needs to know who's calling | new `backend/app/auth.py`, wired into `backend/app/api/routes.py`, `waitlist.py` | M | Auth.js setup |
| Add `user_id` FK to `processed_videos`, scope cache reads/writes and `DISCOVERY_CACHE` by user | Closes the "shared global cache" gap flagged in the audit | `backend/app/models/video.py`, `backend/app/graph/nodes.py:116`, `backend/app/api/routes.py` | M | users table |
| Replace the dead "Log in" link with a real sign-in flow; add a session-aware nav state | Currently a dead `href="#"` anchor | `frontend/src/app/page.tsx`, `frontend/src/app/layout.tsx` | S | Auth.js setup |
| Decide: per-user isolation only, or lightweight "workspace" concept | Affects schema shape now vs. later migration pain | schema design | — | **user decision — see Open Questions** |

**Tests to add:** JWT verification rejects missing/invalid/expired tokens; a user cannot read another user's cached `processed_videos` row; waitlist and health endpoints remain accessible without auth (they should stay public).

---

## Phase 2 — Database & migrations

**Why it matters:** SQLite-in-git and `create_all`-on-startup don't hold up under concurrent users or schema evolution. The async-Postgres upgrade path already exists in the code (`database.py:14-19` auto-upgrades `postgres://` URLs) — it's just never been exercised as the primary path.

| Item | Why | Files | Effort | Depends on |
|---|---|---|---|---|
| Stand up Postgres for local dev + prod (Railway addon, Supabase, or Neon — **user decision**) | SQLite doesn't handle concurrent writers well; already partially supported | infra + `DATABASE_URL` | S | — |
| Initialize Alembic (already a listed dependency, unused) and generate a baseline migration | No migration path exists today; `create_all` can't handle schema evolution safely | new `backend/alembic/`, `backend/alembic.ini` | M | Postgres decision |
| Convert `ProcessedVideo.response_payload` from a JSON-string column to a native `JSONB` column | Currently unindexable/unqueryable (`models/video.py:22-26`) | `backend/app/models/video.py` + migration | S | Alembic |
| Add connection pooling config (pool size, timeout) for the async engine | Needed once multiple workers/replicas share one DB | `backend/app/database.py` | S | Postgres decision |
| Add cache TTL/invalidation to `processed_videos` reads | Currently cached forever once written (audit §Cost/latency) | `backend/app/api/routes.py` | S | — |

**Tests to add:** migration applies cleanly to a fresh DB; existing cache read/write logic (including the cache-poisoning guard from commit `529c3c4`) still behaves correctly against Postgres.

---

## Phase 3 — Concurrency, background jobs, and shared state

**Why it matters:** Today's rate limiter and `DISCOVERY_CACHE` are in-process Python dicts — they silently stop working correctly the moment more than one uvicorn worker or replica runs. Long pipeline runs also currently block an HTTP request/SSE connection for their full duration, which doesn't scale to many concurrent users.

| Item | Why | Files | Effort | Depends on |
|---|---|---|---|---|
| Wire up the already-listed, currently-dead Redis dependency for the rate limiter | `rate_limiter.py`'s sliding window and `middleware.py`'s `RateLimitMiddleware` are in-process only today | `backend/app/rate_limiter.py`, `backend/app/middleware.py`, `backend/app/dependencies.py` | M | Redis hosting decision |
| Replace `DISCOVERY_CACHE` global dict with Redis-backed cache (TTL'd, keyed by `video_id` + relevant params) | Closes the unbounded-memory / no-isolation gap flagged in the audit | `backend/app/graph/nodes.py:116` | S | Redis hosting decision |
| Introduce an async job queue (**recommend `arq`** — Redis-based, async-native, far less operational overhead than Celery, easy to explain in an interview as "a lightweight task queue built on the Redis connection we already need") for long pipeline runs | Decouples the HTTP request lifecycle from a potentially multi-minute pipeline run; enables real horizontal scaling | new `backend/app/worker.py`, changes to `backend/app/api/routes.py` to enqueue + poll/stream job status | L | Redis hosting decision |
| Add per-user rate limiting/quotas (distinct from the existing per-IP limiting) | Needed now that real user identity exists | `backend/app/middleware.py`, `backend/app/rate_limiter.py` | M | Phase 1 (auth) |
| Reconsider SSE design once jobs are queued: either keep SSE reading from a pub/sub channel the worker publishes to, or move to polling a job-status endpoint | Current SSE handler runs the graph inline in the request; that changes once work moves to a queue | `backend/app/api/routes.py`, `frontend/src/components/url-input.tsx` | M | job queue |

**Tests to add:** two concurrent requests for the same video don't cross-contaminate cache; rate limiting still enforces correctly when simulated across "multiple workers" (can be tested by running the limiter against a shared Redis test instance from two client contexts).

---

## Phase 4 — AI system design gap closure

**Why it matters:** This is the section a technical interviewer will scrutinize most closely — it's where the audit found the most concrete, fixable gaps.

| Item | Why | Files | Effort | Depends on |
|---|---|---|---|---|
| Externalize prompts into versioned template files (even a simple `backend/app/prompts/*.py` module with a `PROMPT_VERSION` constant per prompt is enough — no need for a heavyweight prompt-registry service) | Currently hardcoded inline with no versioning (audit §Prompt management) | `backend/app/agents/*.py` → new `backend/app/prompts/` | M | — |
| Either wire up `CLIP_VALIDATION_PROMPT` for real LLM-assisted validation, or delete it and fix the misleading docstring | Currently dead code that contradicts its own documentation | `backend/app/agents/clip_validation_agent.py` | S | — |
| Stop silently swallowing per-batch LLM failures; surface them into `state["errors"]` and reflect partial results in the API response | Currently a user can get fewer clips than expected with no explanation (audit §Error handling) | `backend/app/agents/clip_discovery_agent.py`, `editing_plan_agent.py`, `backend/app/graph/nodes.py` | M | — |
| Make validation failure *fail closed* (or at minimum flag fail-open clips distinctly) instead of silently promoting unvalidated clips | Currently `clip_validation` promotes unverified clips on any exception (audit §Tool use) | `backend/app/graph/nodes.py:257-264` | S | — |
| Add a token-budget guard before batching transcript chunks (switch chunking to token-aware sizing, or at minimum cap batch size by estimated token count) | Currently batches up to ~35 minutes of raw text with no guard | `backend/app/services/chunking_service.py`, `backend/app/agents/clip_discovery_agent.py` | M | — |
| Add an overall request/pipeline timeout | Currently up to ~27 stacked retry attempts possible with no ceiling | `backend/app/graph/workflow.py` or `backend/app/api/routes.py` | S | — |
| Build a small evaluation harness: a golden set of ~10-20 test videos with expected clip characteristics (duration bounds, hook presence, transcript containment), scored via the existing programmatic checks plus an LLM-as-judge pass for subjective quality (hook strength, editing-plan coherence) | Currently **missing entirely** — this is the clearest "we test AI quality, not just code correctness" signal for a portfolio | new `backend/evals/` (dataset + runner), new `tests/test_evals.py` or a separate CI job | L | Phase 0 logging fix (for capturing eval traces) |
| Add per-request token/cost/latency tracking, persisted per request (a simple `llm_calls` table capturing model, tokens in/out, latency, cost estimate is enough — no need for a full observability platform) | Currently **missing entirely** | new `backend/app/models/llm_call.py`, hook into `dependencies.py`'s LLM client construction | M | Phase 2 (Postgres) |
| Enable Gemini token streaming for the discovery/editing-plan calls where the UI can benefit (optional — the SSE graph-state stream can stay as the "pipeline progress" view; this is about the actual model output) | Reduces perceived latency | `backend/app/agents/*.py`, `frontend/src/components/loading-terminal.tsx` | M | — |

**Tests to add:** eval harness runs against the golden set and fails CI if pass rate drops below a threshold; a unit test asserting a stuck/misbehaving LLM call trips the new overall timeout; a regression test for the specific cache-poisoning bug (guard against reintroducing it).

---

## Phase 5 — Production readiness

**Why it matters:** Docker, CI, health checks, and a security pass are what make the rest of this roadmap actually verifiable and demonstrable rather than just "code that exists."

| Item | Why | Files | Effort | Depends on |
|---|---|---|---|---|
| GitHub Actions CI: lint (`ruff`/`eslint`), `pytest`, eval harness | No CI exists today; 88 tests currently only run manually | new `.github/workflows/ci.yml` | M | Phase 4 (evals) |
| `docker-compose.yml` for local dev (backend + Postgres + Redis, frontend run separately via `next dev`) | No compose file exists; onboarding currently requires manually standing up SQLite/no-Redis | new `docker-compose.yml` | S | Phase 2, 3 |
| Delete the redundant root `Dockerfile` (or repurpose it as the compose backend build target) and add a root `.dockerignore` if it's kept | Currently dead/duplicate of `backend/Dockerfile` per audit | `Dockerfile`, new `.dockerignore` | S | — |
| Real health check with dependency checks (DB reachable, Redis reachable) | Current `/health` is a static payload | `backend/app/main.py:66-73` | S | Phase 2, 3 |
| Security pass: confirm CORS origin list is still correct once auth ships, decide CSRF posture (likely N/A if staying Bearer-JWT/stateless — document the decision explicitly), confirm rate limiting + auth stack order is still correct | Auth changes the threat model | `backend/app/middleware.py`, `backend/app/config.py` | S | Phase 1 |
| Fix documentation drift: update `docs/LANGGRAPH_PIPELINE.md` to reflect the Supadata-led fallback chain and structured editing-plan output; either update or clearly mark `clipforge_langgraph_prd.md`/`.planning/PROJECT.md` as historical/pre-implementation artifacts | Currently actively misleading if read as current-state docs | `docs/LANGGRAPH_PIPELINE.md`, `clipforge_langgraph_prd.md`, `.planning/PROJECT.md` | S | — |
| Expand README with the new architecture (auth, Postgres, Redis, job queue), a rendered Mermaid diagram, and an explicit "design decisions & trade-offs" section | This is the document a reviewer reads first | `README.md` | M | all prior phases |
| Add minimal frontend tests (Vitest + React Testing Library for the waitlist form and URL input at minimum) | Currently zero frontend tests | new `frontend/vitest.config.ts`, `frontend/src/**/*.test.tsx` | M | — |

---

## Suggested sequencing

Phase 0 (hygiene) can start immediately and in parallel with everything else. Phase 1 (auth) and Phase 2 (database) should go before Phase 3 (concurrency/jobs), since jobs and per-user quotas need real identity and a production-shaped database first. Phase 4 (AI system design) is largely independent and can be interleaved with Phases 1-3. Phase 5 (production readiness) closes everything out and depends on the others being substantially done.

---

## Open questions for you

1. **OAuth/session approach** — confirm Auth.js (NextAuth v5) on the frontend issuing a Bearer JWT the backend verifies, as recommended above, vs. a backend-driven OAuth flow with cross-domain cookies?
2. **Postgres hosting** — Railway's Postgres addon (keeps everything on one platform), Supabase, or Neon?
3. **Redis hosting** — Railway addon, Upstash, or another provider?
4. **Job queue** — `arq` (recommended, lightweight, Redis-native) vs. Celery (heavier, more ecosystem tooling) vs. skipping a real queue for now and just adding an overall timeout?
5. **Multi-tenancy shape** — is per-user isolation sufficient, or do you want a "workspace/team" concept (multiple users sharing clips/results)? This affects the Phase 1 schema design.
6. **CI/hosting for the eval harness** — GitHub Actions is assumed; confirm, and let me know if there's a budget/quota concern about the eval harness making real (billed) LLM calls in CI vs. using a fixture/recorded-response mode.
7. **Frontend hosting** — staying on Vercel? (Assumed yes — no signal otherwise.)

Once you've weighed in on these (or told me to just make the calls), I'll start on Phase 0 as the first reviewable commit series.
