# Pitfalls Research — ClipForge AI

## Critical Pitfalls

### 1. LLM Hallucination in Clip Extraction
**Risk**: LLM generates clip text that doesn't exist in the transcript.
**Warning signs**: Clip text passes a casual read but fails exact string match.
**Prevention**:
- Validate every clip against the original transcript using exact substring matching
- Use fuzzy matching as a secondary check (catch minor formatting differences)
- Include the full transcript chunk in the prompt context so the LLM copies verbatim
- Prompt engineering: explicitly instruct "copy text EXACTLY as it appears"
**Phase**: Clip Discovery + Validation nodes

### 2. youtube-transcript-api Fragility
**Risk**: Library is unofficial — YouTube changes can break it without warning.
**Warning signs**: Sudden `VideoUnavailable` errors, empty transcripts.
**Prevention**:
- Wrap transcript fetching in robust error handling with clear user messaging
- Cache transcripts in Redis (don't re-fetch)
- Design the transcript interface as an abstraction (easy to swap providers)
- Add rate limiting (1-2 second delays between requests)
- Consider fallback to manually uploaded transcripts in future
**Phase**: Transcript Retrieval node

### 3. Transcript Quality Issues
**Risk**: Auto-generated YouTube captions have errors, missing punctuation, wrong word boundaries.
**Warning signs**: Clip text is garbled, timestamps don't align.
**Prevention**:
- Prefer manually-uploaded captions over auto-generated when available
- Clean and normalize transcript text before processing
- Merge fragmented segments with proper sentence boundaries
- Validate timestamp continuity
**Phase**: Transcript Processing node

### 4. Infinite Retry Loops
**Risk**: Validation keeps failing, LLM keeps generating bad clips, infinite loop.
**Warning signs**: Retry count exceeds reasonable limits, same errors repeating.
**Prevention**:
- Hard cap at 3 retries per validation cycle
- Track which clips failed and why — pass failure reasons to next attempt
- After max retries, return best available clip with a quality warning
- Log all retry attempts for debugging
**Phase**: Validation Loop

### 5. Context Window Overflow
**Risk**: Long podcast transcripts (2-3 hours) exceed LLM context limits.
**Warning signs**: Truncated responses, API errors, degraded reasoning quality.
**Prevention**:
- Chunk transcripts into manageable segments (5-10 minute windows)
- Use a two-stage approach: first scan all chunks for candidates, then deep-analyze top candidates
- Track token counts before sending to LLM
- Choose models with large context windows (128K+)
**Phase**: Transcript Processing + Clip Discovery

### 6. Prompt Injection from Transcript Content
**Risk**: Podcast guest says something that acts as a prompt injection.
**Warning signs**: LLM output changes behavior or ignores instructions.
**Prevention**:
- Clearly delimit transcript content in prompts (XML tags, markdown blocks)
- Use system prompts to establish strong behavioral boundaries
- Validate output structure before processing
**Phase**: All LLM nodes

### 7. OpenRouter Rate Limits and Costs
**Risk**: Unexpected API costs or rate limiting during development.
**Warning signs**: 429 errors, surprisingly high bills.
**Prevention**:
- Use cheaper models for development/testing, strong models for production
- Implement token budgets and cost tracking
- Cache LLM responses during development
- Set up spending alerts on OpenRouter
**Phase**: All LLM nodes

### 8. Timestamp Misalignment
**Risk**: Clip timestamps don't match actual video positions.
**Warning signs**: Clips start/end at wrong moments when cut from video.
**Prevention**:
- Preserve original transcript timestamps throughout the pipeline
- Validate timestamp continuity after merging segments
- Include timestamp ranges in clip output for easy verification
**Phase**: Transcript Processing + Output Formatter

## Medium-Risk Pitfalls

### 9. Poor Clip Quality (Subjective)
**Prevention**: Include explicit viral criteria in prompts (hook, emotional peak, curiosity gap, payoff). Provide examples of good vs bad clips.

### 10. Database Schema Evolution
**Prevention**: Use Alembic migrations from day 1. Keep schema simple and extensible with JSONB for flexible fields.

### 11. Streamlit Performance
**Prevention**: Use `st.spinner()` for long operations. Consider async polling instead of blocking calls. Cache results with `@st.cache_data`.

---
*Researched: 2026-03-11*
