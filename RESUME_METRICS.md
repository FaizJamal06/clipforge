# ClipForge — Resume Metrics (evidence-backed)

Generated 2026-10-05 from the repo at commit `8066e46`, git history, and commands run locally.
No paid API calls were made and no code was changed.

**Project:** AI podcast-clipping SaaS. It takes a YouTube URL, finds viral 40–60s moments, and generates a beat-by-beat editing blueprint.
Stack: FastAPI · LangGraph · LangChain · Google Gemini 2.5 Flash · Pydantic · SQLAlchemy (async) · Next.js 16 / React 19 · Auth.js · Stripe · Docker · Render + Vercel.

## Ownership note (read first)

- Solo repo: `git shortlog -sne --all` → **43 commits, all by FaizJamal06 &lt;faizjamal1306@gmail.com&gt;** (2026-03-11 → 2026-10-02).
- **19 of the 43 commits** (everything from `aeb3652`, 2026-09-21 onward) carry a `Co-Authored-By: Claude` trailer. They were written with an AI coding agent in a directed session.
  Command: `git log main --grep="Co-Authored-By: Claude" --format=%h | wc -l` → `19`.
- `git blame` over current app, test and frontend code shows **1,047 of 8,671 lines (12%)** were last touched by those AI-co-authored commits.
  The other 7,624 come from earlier commits. Those have no AI trailer, but `AI_INSIGHTS.md` says coding agents were used throughout, so a missing trailer does **not** prove hand-written code.
- Ownership tags below: **mine** = solo repo, pre-2026-09-21; **mine (AI-co-authored)** = from the trailer-marked commits. Be ready to explain both in an interview.

## Metrics

| Metric | Value | Evidence | Status | Ownership |
|---|---|---|---|---|
| Automated tests | **106 passed, 0 failed, 0 skipped** (4.9 s) | `backend/venv/Scripts/python.exe -m pytest -q` → `106 passed, 2 warnings in 4.89s` | verified | mine; 18 of 106 added in AI-co-authored commits (suite was 88 before 2026-09-21, the count I observed at session start; also stated in commit `405f182`) |
| Tests per file | auth 17 (token 6 · user 3 · isolation 2 · paywall 4 incl. 1 demo-data check · CORS 2) · services 20 · state 2 · today 48 · validation 9 · workflow 10 | `pytest --collect-only -q` | verified | test_auth.py: mine (AI-co-authored); rest: mine |
| LangGraph pipeline stages | **7 nodes, 6 conditional edges**, incl. a validation→discovery retry loop | `backend/app/graph/workflow.py:74-80` (add_node ×7), `add_conditional_edges` ×6 | verified | mine |
| LLM agents | **2 LLM call sites** (clip discovery, editing plan), both Pydantic structured output | `agents/clip_discovery_agent.py:115`, `agents/editing_plan_agent.py:142` (`with_structured_output`) | verified | mine |
| Pydantic schemas for model output | 7 classes | `grep "class .*(BaseModel)" agents/*.py` | verified | mine |
| Transcript fallback layers | **4 strategies**: Supadata → youtube-transcript-api → InnerTube → YouTube Data API v3 | `services/transcript_service.py:564` `fetch_transcript()` calls `_fetch_via_supadata` (510), `_fetch_via_ytt_library` (664), `_fetch_via_innertube` (373), `_fetch_via_youtube_api` (165) | verified | mine |
| Retry layers on LLM calls | 3 stacked: client `max_retries`, agent loop ×3, graph retry ×3 | `dependencies.py:48`, `clip_discovery_agent.py:139`, `editing_plan_agent.py:156`, `config.py:55` | verified | mine |
| Model-output repair | incomplete clips detected and batch retried; 503 back-off | `clip_discovery_agent.py:41` (`is_complete`), `:146`, `:172`; commit `2c16a76` | verified | mine (AI-co-authored) |
| Prompt-injection filter | **23 regex patterns** | `LLM_API_KEY=x python -c "import app.security as s; print(len(s._INJECTION_PATTERNS))"` → `23`; `security.py:20` | verified | mine |
| Security middleware | 4 layers: security headers, IP rate limit, API-key, CORS | `main.py:55-64` | verified | mine |
| IP rate limiting | 20 req/min, burst 5 per 2 s | `config.py:83-84` | verified | mine |
| LLM rate limiter | 4 req/min shared sliding window (Gemini free tier) | `config.py:61`, `rate_limiter.py` | verified | mine |
| Fuzzy anti-hallucination check | clip must match transcript at ≥ 0.5 similarity | `agents/clip_validation_agent.py:139`, `:214` | verified (it's a threshold, not a result) | mine |
| Waitlist abuse filtering | honeypot + 12 blocked disposable domains | `models/waitlist.py:41-46` | verified | mine |
| API endpoints | **8 working** (+1 stub returning 501) | `grep -nE "@(router|app)\.(get|post)" api/*.py main.py` → 9; `/status/{job_id}` is a 501 stub (`routes.py:373`) | verified | mine; `/me`, `/billing/*`: mine (AI-co-authored) |
| Auth + data isolation | Google OAuth (Auth.js) → HS256 JWT verified by FastAPI; per-user cache rows `(user_id, video_id)` | `backend/app/auth.py`, `models/video.py`, `frontend/src/auth.ts`; tests in `tests/test_auth.py` | verified | mine (AI-co-authored) |
| Paywall | Stripe Checkout, signature-verified webhook grants Pro; 402 for free users | `api/billing.py`, `auth.py:91` (`require_pro`) | verified (code); **Stripe never exercised with real keys** | mine (AI-co-authored) |
| Editing-plan depth | 12–13 beats per clip, each with shot / sound / transition | `frontend/src/data/demo.json` (real pipeline output, 2 clips: 13 and 12 segments) | verified | mine (AI-co-authored) |
| Codebase size (non-blank lines, incl. comments) | Python 4,368 (app 3,050 · tests 868 · scripts 450); TS/TSX 2,183; CSS 1,268 | `git ls-files` minus tooling dirs / lockfiles / generated JSON, `grep -cv '^\s*$'` | verified (weak resume metric) | see ownership note |
| Deployment | Backend Docker on Render, frontend on Vercel | `backend/Dockerfile`; live checks below | verified | mine; Render move: AI-co-authored |
| Live URLs (2026-10-05 04:33 UTC) | Vercel `clipforge-eosin.vercel.app` 200; Render `clipforge-0qw4.onrender.com/health` 200 | `curl` checks (Render needed a cold start, see below) | verified | — |
| CI | Only `.github/workflows/keep-warm.yml` (a cron ping). **No test/lint CI.** | repo tree | verified | mine (AI-co-authored) |
| Git history | 43 commits over ~7 months | `git rev-list --count main`; first `11ab036` 2026-03-11, last `8066e46` 2026-10-02 | verified | mine |

## Ask me (would strengthen the resume, not in the repo)

1. **End-to-end pipeline latency.** It was never measured. `backend/scripts/benchmark_pipeline.py` measures it but calls live Gemini and Supadata (credits), so I didn't run it. Run it yourself a few times and record the median.
2. **Transcript reliability before/after the fallback chain.** `AI_INSIGHTS.md:300` claims "~50% failure rate → near-100%" but no logs back it. Check your old Railway logs from April.
3. **Real usage.** Any waitlist signups or users from the old Railway Postgres deployment? (The current Render database is ephemeral; see below.)
4. **Clip quality.** No eval exists. Even 10–20 hand-labelled clips with a hit rate would be the strongest AI-engineering metric you could add.
5. **Cost per video.** Not tracked. Check the Google AI Studio usage dashboard after a run.

## Do not use

| Number | Why |
|---|---|
| "under 10 seconds" / "1–3 hours manual" (`README.md:12`) | Never measured anywhere; the manual-time figure is unsourced. Real runs are gated by a 4 req/min limiter plus retries, so 10 s is implausible. |
| "~50% → near-100% transcript reliability" (`AI_INSIGHTS.md:300`) | Doc-only claim, no logs. Use only if you can produce the data (ask #2). |
| 908 ms demo click → result (measured this session) | The demo is a static JSON bundled into the page; no AI runs. |
| 0.155 s warm `/health` | Trivial endpoint, not pipeline latency. |
| 9.0–10.0 virality scores in the demo | The model's self-assigned scores, not evaluated quality. |
| Waitlist count / user count from production | Render free tier runs SQLite on an ephemeral disk; data resets on every restart or redeploy. |
| "3 AI agents" | The validation agent's LLM prompt (`clip_validation_agent.py:48`) is defined but never invoked; validation is programmatic. Say 2 LLM agents + a programmatic validator. |
| "9 endpoints" | One is a 501 stub; say 8. |
| "CI pipeline" | The only workflow is a keep-warm cron; there is no test CI. |
| "Always-on / no cold starts" | Measured cold start: **39.3 s** (first `/health` after idle) vs 0.155 s warm. The keep-warm cron ran only **15 times** between 2026-10-02 18:12 and 2026-10-05 00:26 UTC (~324 expected at every 10 min), per the GitHub Actions API. |

## Resume bullets (verified only)

- Built a 7-node LangGraph pipeline with 2 Gemini agents emitting Pydantic-validated structured output, turning YouTube podcasts into timestamped viral clips and editing blueprints.
- Engineered a 4-layer transcript fallback (Supadata → youtube-transcript-api → InnerTube → YouTube Data API) so ingestion survives individual source failures and IP blocks.
- Hardened a FastAPI backend with 4 middleware layers, 23-pattern prompt-injection filtering, per-IP rate limiting and 3-tier LLM retries; 106 automated tests passing.
- *(AI-co-authored — use only if you can explain it end to end)* Added Google OAuth with backend JWT verification, per-user data isolation and a Stripe-gated Pro tier, covered by 14 auth, isolation and paywall tests.

## Interview notes

1. **Gemini silently dropped schema fields.** Optional fields in the structured-output schema were skipped by the model, so clips came back with 0:00 timestamps, empty hooks and a flat 7.0 score. Making the fields required made Gemini fail whole batches instead. The fix was a permissive schema plus a post-hoc completeness check and retry (`clip_discovery_agent.py:41`, commit `2c16a76`). It's a good story about validating LLM output beyond "it parsed".
2. **Free-tier trade-offs, with numbers.** Measured cold start 39.3 s vs 0.155 s warm. The GitHub cron keep-alive ran ~5% of its scheduled times, so instead of fighting the infra, the demo data was moved into the frontend bundle and recruiters never hit the backend. Related "works on my machine" bug: a clean Docker build pulled SQLAlchemy 2.1, which no longer bundles `greenlet`, crashing startup (`88143dc`).
3. **Honest gaps.** There is no eval harness, so quality is unmeasured. A README speed claim was never tested. The "validation agent" doesn't actually call the LLM. There was also a real cache-poisoning bug (failed runs cached and served forever), fixed in `529c3c4`. Owning these reads better than defending them.
