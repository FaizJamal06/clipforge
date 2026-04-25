"""
ClipForge AI — Clip Discovery Agent

Uses LLM to analyze transcript chunks and identify the most viral
40-60 second segments. Each selected clip must be verbatim, continuous,
and contain a strong hook + payoff structure.
"""

import json
import logging
import asyncio
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from app.security import PromptInjectionGuard
from app.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


# ----- Structured Output Schema ----- #

class DiscoveredClip(BaseModel):
    """Schema for a single discovered clip candidate."""
    clip_text: str = Field(description="Exact verbatim text from the transcript.")
    start_time: float = Field(default=0.0, description="Estimated start timestamp in seconds.")
    end_time: float = Field(default=0.0, description="Estimated end timestamp in seconds.")
    duration: float = Field(default=50.0, description="Clip duration in seconds (should be 40-60).")
    virality_score: float = Field(default=7.0, description="Virality score from 1-10.")
    virality_reasoning: str = Field(default="", description="Explanation of why this clip is likely to go viral.")
    hook: str = Field(default="", description="The opening hook that grabs attention.")
    payoff: str = Field(default="", description="The satisfying conclusion or punchline.")


class ClipDiscoveryOutput(BaseModel):
    """Schema for the clip discovery agent output."""
    clips: list[DiscoveredClip] = Field(description="Top 3 viral clip candidates, ranked by virality.")


# ----- Prompt Template ----- #

CLIP_DISCOVERY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert viral content strategist specializing in short-form podcast clips.

Your task is to analyze a podcast transcript and identify the BEST most viral 40-60 second segments.

RULES:
1. Each clip MUST be an EXACT verbatim copy from the transcript — do NOT paraphrase or modify any words.
2. Each clip MUST be a continuous segment — do NOT splice together non-adjacent parts.
3. Each clip MUST be 40-60 seconds in duration (estimate based on ~150 words per minute speaking rate).
4. Each clip MUST contain a strong HOOK (attention-grabbing opening) and a PAYOFF (satisfying conclusion).
5. Use the timestamps provided in [MM:SS] format to estimate start_time and end_time in seconds.

VIRAL CRITERIA (ranked by importance):
- Emotional peaks (surprise, humor, outrage, awe)
- Curiosity gaps (statements that make viewers need to hear more)
- Contrarian or controversial takes
- Personal stories with universal resonance
- "Quotable" moments that stand alone without context
- Dramatic revelations or plot twists in stories

Return the best clips found in each segment. Explain your reasoning for the selection.
The clip_text must be COPIED EXACTLY from the transcript text — character for character.""",
    ),
    (
        "human",
        """Analyze the following podcast transcript segment and identify up to 2 viral clips (40-60 seconds each).

<transcript>
{transcript_chunks}
</transcript>

Return up to 2 clips as structured output with verbatim text, timestamps, duration, and virality reasoning.""",
    ),
])


# ----- Agent Logic ----- #

def _extract_retry_after(error_msg: str) -> float:
    """Parse 'retry in Xs' from a 429 error message."""
    match = re.search(r'retry in (\d+(?:\.\d+)?)s', str(error_msg), re.IGNORECASE)
    return float(match.group(1)) if match else 0


async def run(transcript_chunks: list[str], llm: BaseChatModel) -> ClipDiscoveryOutput:
    """Execute the clip discovery agent.

    Uses larger batches (~35 min of audio per batch) and processes them
    sequentially through a global rate limiter to stay within Gemini
    free-tier quotas while minimizing total latency.

    Args:
        transcript_chunks: Processed transcript chunks to analyze.
        llm: LangChain BaseChatModel instance.

    Returns:
        ClipDiscoveryOutput with top viral clip candidates.
    """
    structured_llm = llm.with_structured_output(ClipDiscoveryOutput)
    chain = CLIP_DISCOVERY_PROMPT | structured_llm
    rate_limiter = get_rate_limiter()

    all_candidate_clips = []
    
    # Batch size from config — larger batches = fewer API calls
    # Default 7 chunks/batch reduces a 1-hour podcast to ~3 LLM calls
    from app.config import get_settings
    BATCH_SIZE = get_settings().llm_batch_size
    batches = []
    for i in range(0, len(transcript_chunks), BATCH_SIZE):
        batch = transcript_chunks[i:i + BATCH_SIZE]
        # Sanitize each chunk to prevent prompt injection
        sanitized_batch = [PromptInjectionGuard.sanitize(chunk) for chunk in batch]
        combined_transcript = "\n\n---\n\n".join(sanitized_batch)
        batches.append(combined_transcript)

    logger.info(f"Clip discovery: {len(transcript_chunks)} chunks → {len(batches)} batches (batch size {BATCH_SIZE})")

    for batch_idx, batch_text in enumerate(batches):
        label = f"discovery batch {batch_idx + 1}/{len(batches)}"
        logger.info(f"Running {label}...")

        for attempt in range(3):
            try:
                # Acquire a rate-limiter slot before calling the LLM
                await rate_limiter.acquire(label)
                result = await chain.ainvoke({"transcript_chunks": batch_text})

                clips = result.clips if getattr(result, "clips", None) else []
                all_candidate_clips.extend(clips)
                logger.info(f"{label}: found {len(clips)} clips")
                break  # Success — move to next batch

            except Exception as e:
                error_str = str(e)
                logger.error(f"Error in {label} (attempt {attempt+1}): {e}")

                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    retry_after = _extract_retry_after(error_str)
                    rate_limiter.report_rate_limit_error(retry_after)
                    # Wait for the back-off period then retry
                    wait = max(retry_after, 15.0) + 2
                    logger.info(f"{label}: rate limited, waiting {wait:.0f}s before retry")
                    await asyncio.sleep(wait)
                elif "402" in error_str:
                    logger.error(
                        f"{label}: billing/quota error (402) — "
                        "check your API plan. Skipping batch."
                    )
                    break
                else:
                    break  # Non-retryable error

    # Deduplicate in case overlapping chunks caused duplicate discoveries
    unique_texts = set()
    deduped_clips = []
    for clip in all_candidate_clips:
        if isinstance(clip, dict):
            text = clip.get("clip_text", "")
        else:
            text = getattr(clip, "clip_text", "")
        if text and text not in unique_texts:
            unique_texts.add(text)
            deduped_clips.append(clip)

    # Sort clips descending by virality score
    def get_score(x):
        return x.get("virality_score", 0.0) if isinstance(x, dict) else getattr(x, "virality_score", 0.0)
        
    deduped_clips.sort(key=get_score, reverse=True)

    # Return up to 10 sorted clips 
    final_clips = deduped_clips[:10]

    logger.info(f"Discovered {len(final_clips)} candidate clips across {len(batches)} batches")
    return ClipDiscoveryOutput(clips=final_clips)

