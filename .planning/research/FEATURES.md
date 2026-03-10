# Features Research — ClipForge AI

## Table Stakes (Must Have — Users Expect These)

### Transcript Handling
- **YouTube URL input with validation** — Core entry point
- **Automatic transcript extraction** — No manual upload required
- **Timestamp preservation** — Clips must map back to video timestamps
- **Transcript cleaning** — Remove filler words, merge fragmented segments

### Clip Discovery
- **Viral moment detection** — Emotional peaks, curiosity gaps, storytelling hooks
- **Verbatim clip extraction** — Must be exact transcript text, no paraphrasing
- **Clip length targeting** — 40–60 second sweet spot for short-form
- **Hook + payoff structure** — Every clip needs a strong opening and satisfying conclusion
- **Multiple clip output** — Top 3 ranked by virality potential

### Validation
- **Transcript containment check** — Clip text must exist in original transcript
- **Continuity check** — Clip must be a continuous segment, not spliced
- **Duration validation** — Clip must be within 40–60 second range
- **Hallucination detection** — Reject any LLM-invented text

### Output
- **Clip script with timestamps** — Start/end times for each clip
- **Editing plan per clip** — B-roll, captions, pacing
- **Structured, copyable output** — Easy for editors to use

## Differentiators (Competitive Advantage)

- **Virality scoring with reasoning** — Explain WHY a clip is viral (emotional intensity, storytelling quality, curiosity gap score)
- **B-roll suggestions** — Context-aware visual recommendations per clip segment
- **Caption strategy** — Hook captions, emphasis moments, call-to-action placement
- **Pacing instructions** — Cut timing, zoom suggestions, visual rhythm
- **Processing history** — Database of past runs for comparison

## Anti-Features (Deliberately NOT Building)

- **Auto video cutting** — Requires FFmpeg integration, high complexity, deferred
- **AI-generated B-roll** — Requires video diffusion models, out of scope
- **Multi-language support** — English first, expand later
- **User accounts / auth** — Not needed for v1 portfolio project
- **Batch processing** — Single URL at a time for v1

## Feature Dependencies
```
URL Input → Transcript Extraction → Transcript Processing → Clip Discovery → Validation → Editing Plan → Output
                                                                    ↑                |
                                                                    └── retry loop ──┘
```

---
*Researched: 2026-03-11*
