# ClipForge AI — LangGraph Pipeline Deep Dive

## The Big Picture

ClipForge uses **three technologies** that work together like layers of a cake:

| Layer | Technology | Role |
|-------|-----------|------|
| **Orchestration** | **LangGraph** | Controls _what happens when_ — defines the node graph, edges, and retry logic |
| **LLM Interface** | **LangChain** | Talks to the AI model — sends prompts, parses structured outputs |
| **LLM Model** | **Google Gemini** | The actual AI brain that understands text and finds viral clips |

> Think of it as: **LangGraph** is the assembly line, **LangChain** is the robot arm, and **Gemini** is the brain.

---

## Node Graph — How It Flows

```mermaid
flowchart TD
    START([🎬 User submits YouTube URL]) --> N1

    N1["⬛ Node 1: input_handler<br/><i>Validates URL, extracts video ID</i>"]
    N2["⬛ Node 2: transcript_retrieval<br/><i>Fetches transcript from YouTube</i>"]
    N3["⬛ Node 3: transcript_processing<br/><i>Cleans filler words, chunks text</i>"]
    N4["🤖 Node 4: clip_discovery<br/><i>AI scans for viral moments</i>"]
    N5["✅ Node 5: clip_validation<br/><i>Validates 40-60s rules + timestamps</i>"]
    N6["📋 Node 6: editing_plan<br/><i>AI generates editing blueprint</i>"]
    N7["📤 Node 7: output_formatter<br/><i>Merges clips + plans into final response</i>"]

    N1 --> N2 --> N3 --> N4 --> N5

    N5 -->|"All clips valid ✅"| N6
    N5 -->|"All failed + retries left 🔄"| N4

    N6 --> N7 --> DONE([✨ Results streamed to frontend via SSE])

    style N4 fill:#1a1a2e,stroke:#FF4F1F,color:#fff
    style N5 fill:#1a1a2e,stroke:#00C4A7,color:#fff
    style N6 fill:#1a1a2e,stroke:#FFD60A,color:#fff
```

---

## What Each Node Does

### ⬛ Node 1 — `input_handler` ([nodes.py:29](../backend/app/graph/nodes.py#L29))
**Purpose:** Validates the YouTube URL and extracts the video ID.

```
Input:  state.youtube_url = "https://youtube.com/watch?v=abc123"
Output: state.video_id = "abc123", state.status = "input_validated"
```
No AI involved — just regex parsing.

---

### ⬛ Node 2 — `transcript_retrieval` ([nodes.py:53](../backend/app/graph/nodes.py#L53))
**Purpose:** Fetches the full transcript from YouTube using `youtube-transcript-api`.

```
Input:  state.video_id = "abc123"
Output: state.transcript = [{text: "...", start: 0.0, duration: 5.2}, ...]
```
No AI — uses the `youtube-transcript-api` Python library.

---

### ⬛ Node 3 — `transcript_processing` ([nodes.py:84](../backend/app/graph/nodes.py#L84))
**Purpose:** Cleans the raw transcript (removes filler words like "um", "uh"), merges speaker segments, and chunks the text into overlapping windows.

```
Input:  state.transcript = [{text: "um so basically...", ...}, ...]
Output: state.transcript_chunks = ["chunk 1 (40-60s of text)...", "chunk 2...", ...]
```
No AI — pure Python text processing.

---

### 🤖 Node 4 — `clip_discovery` ([nodes.py:118](../backend/app/graph/nodes.py#L118))
**Purpose:** This is where LangChain + Gemini kick in. Sends transcript chunks to the AI and asks:
> _"Find the most viral 40-60 second clip in this text. Look for strong hooks, counterintuitive takes, emotional moments, and cliffhangers."_

```
Input:  state.transcript_chunks = ["chunk1...", "chunk2...", ...]
Output: state.candidate_clips = [{clip_text, start_time, end_time, virality_score, hook, payoff}, ...]
```

**How it works internally:**
1. `get_llm_client()` creates a `ChatGoogleGenerativeAI` instance (LangChain)
2. The agent sends a structured prompt with transcript chunks
3. Gemini returns structured JSON with clip candidates
4. Results are cached in memory per video ID for "Load More" requests

---

### ✅ Node 5 — `clip_validation` ([nodes.py:204](../backend/app/graph/nodes.py#L204))
**Purpose:** Validates each discovered clip against strict rules:
- Duration must be 40-60 seconds
- Timestamps must exist in the real transcript
- Text must match actual transcript content

```
Input:  state.candidate_clips = [{clip_text: "...", start_time: 120.0, ...}]
Output: state.validated_clips = [...], state.failed_clips = [...]
```

**Retry Logic:** If ALL clips fail validation and retries remain, the graph loops BACK to Node 4 (clip_discovery) to try again.

---

### 📋 Node 6 — `editing_plan` ([nodes.py:267](../backend/app/graph/nodes.py#L267))
**Purpose:** For each validated clip, asks Gemini to create a detailed editing blueprint:
> _"Generate a frame-perfect editing plan: cut points, caption suggestions, B-roll cues, music fade points, and platform-specific tips."_

```
Input:  state.validated_clips = [{clip_text: "...", ...}]
Output: state.editing_plans = [{clip_index: 0, raw_plan: "0:00-0:03 HOOK: Jump cut to..."}, ...]
```

---

### 📤 Node 7 — `output_formatter` ([nodes.py:308](../backend/app/graph/nodes.py#L308))
**Purpose:** Merges validated clips with their editing plans into the final response format.

```
Input:  state.validated_clips + state.editing_plans
Output: state.status = "completed"
```

---

## The Shared State

All 7 nodes share a single `ClipForgeState` object ([state.py](../backend/app/graph/state.py)). Each node reads what it needs and writes its outputs back:

```mermaid
flowchart LR
    subgraph State["ClipForgeState (TypedDict)"]
        A[youtube_url]
        B[video_id]
        C[transcript]
        D[transcript_chunks]
        E[candidate_clips]
        F[validated_clips]
        G[failed_clips]
        H[editing_plans]
        I[retry_count]
        J[errors]
        K[status]
    end

    N1["input_handler"] -->|writes| B
    N2["transcript_retrieval"] -->|writes| C
    N3["transcript_processing"] -->|writes| D
    N4["clip_discovery"] -->|writes| E
    N5["clip_validation"] -->|writes| F
    N5 -->|writes| G
    N6["editing_plan"] -->|writes| H
```

---

## The Conditional Retry Loop

This is what makes LangGraph special — it's not just a linear chain. There's a **conditional edge** after validation:

```python
# workflow.py:29-51
def should_retry_validation(state):
    if validated_clips or retry_count >= max_retries:
        return "continue"    # → editing_plan
    if failed_clips and retry_count < max_retries:
        return "retry"       # → clip_discovery (loop back!)
    return "continue"
```

```mermaid
flowchart LR
    V["clip_validation"] -->|"has valid clips?"| D1{Decision}
    D1 -->|"YES → continue"| E["editing_plan"]
    D1 -->|"NO + retries left → retry"| C["clip_discovery"]
    D1 -->|"NO + max retries → continue"| E
```

This means the AI gets **multiple chances** to find good clips if the first attempt produces invalid results.

---

## How SSE Streaming Works

The frontend doesn't wait for the entire pipeline to finish. Instead, it uses **Server-Sent Events** to receive real-time updates:

```mermaid
sequenceDiagram
    participant F as Frontend (Next.js)
    participant A as API (FastAPI)
    participant G as LangGraph Pipeline

    F->>A: GET /api/v1/process/stream?youtube_url=...
    A->>G: graph.astream(initial_state)

    loop For each node execution
        G-->>A: State update (status change)
        A-->>F: SSE: {"type": "update", "status": "transcript_retrieved"}
    end

    G-->>A: Final state
    A-->>F: SSE: {"type": "complete", "data": {clips, editing_plans}}
    F->>F: Navigate to /result page
```

The key line is in [routes.py:147](../backend/app/api/routes.py#L147):
```python
async for state in graph.astream(initial_state, stream_mode="values"):
    yield f"data: {json.dumps({'type': 'update', 'status': status})}\n\n"
```

---

## Technology Stack Summary

```mermaid
flowchart TB
    subgraph Frontend["Frontend (Vercel)"]
        UI["Next.js + React"]
        SSE["EventSource API"]
    end

    subgraph Backend["Backend (Railway)"]
        API["FastAPI + Uvicorn"]
        LG["LangGraph (Orchestration)"]
        LC["LangChain (LLM Interface)"]
        DB[(PostgreSQL Cache)]
    end

    subgraph External["External Services"]
        YT["YouTube Transcript API"]
        GM["Google Gemini AI"]
    end

    UI -->|"SSE stream"| API
    API --> LG
    LG -->|"Node 2"| YT
    LG -->|"Nodes 4,5,6"| LC
    LC -->|"API calls"| GM
    LG -->|"Cache results"| DB
```

| What | Technology | Why |
|------|-----------|-----|
| **LangGraph** | Directed graph engine | Lets us define nodes, edges, conditional loops, and stream state updates in real-time |
| **LangChain** | LLM abstraction layer | Provides `ChatGoogleGenerativeAI` — handles prompt formatting, structured output parsing, retries, and token management |
| **Google Gemini** | Large Language Model | The AI that actually reads transcripts and identifies viral moments / generates editing plans |
| **FastAPI** | Web framework | Serves the SSE stream and REST endpoints |
| **youtube-transcript-api** | Python library | Fetches real transcripts from YouTube (no AI needed) |
