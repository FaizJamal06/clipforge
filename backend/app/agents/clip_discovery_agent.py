"""
ClipForge AI — Clip Discovery Agent

Uses LLM to analyze transcript chunks and identify the most viral
40-60 second segments. Each selected clip must be verbatim, continuous,
and contain a strong hook + payoff structure.
"""

import json
import logging
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from app.security import PromptInjectionGuard

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

async def run(transcript_chunks: list[str], llm: BaseChatModel) -> ClipDiscoveryOutput:
    """Execute the clip discovery agent.

    Invokes the LLM with the discovery prompt and forces structured output.
    Processes batches in parallel to dramatically reduce latency.

    Args:
        transcript_chunks: Processed transcript chunks to analyze.
        llm: LangChain BaseChatModel instance.

    Returns:
        ClipDiscoveryOutput with top viral clip candidates.
    """
    structured_llm = llm.with_structured_output(ClipDiscoveryOutput)
    chain = CLIP_DISCOVERY_PROMPT | structured_llm

    all_candidate_clips = []
    
    # Process in batches of 3 chunks (~15 minutes of audio)
    BATCH_SIZE = 3
    batches = []
    for i in range(0, len(transcript_chunks), BATCH_SIZE):
        batch = transcript_chunks[i:i + BATCH_SIZE]
        # Sanitize each chunk to prevent prompt injection
        sanitized_batch = [PromptInjectionGuard.sanitize(chunk) for chunk in batch]
        combined_transcript = "\n\n---\n\n".join(sanitized_batch)
        batches.append(combined_transcript)

    async def process_batch(batch_idx: int, text: str):
        logger.info(f"Running clip discovery on chunk batch {batch_idx + 1}...")
        for attempt in range(3):
            try:
                # Stagger requests by 500ms to prevent instant 429 limits
                await asyncio.sleep(batch_idx * 0.5) 
                result = await chain.ainvoke({"transcript_chunks": text})
                return result.clips if getattr(result, "clips", None) else []
            except Exception as e:
                logger.error(f"Error processing batch {batch_idx + 1} (Attempt {attempt+1}): {e}")
                if "429" in str(e) or "402" in str(e):
                    # Rate limit or token timeout, exponential backoff
                    await asyncio.sleep(4 * (attempt + 1))
                else:
                    break
        return []

    # Execute all batches in parallel
    tasks = [process_batch(i, batch_text) for i, batch_text in enumerate(batches)]
    results_list = await asyncio.gather(*tasks)
    
    for clips in results_list:
        all_candidate_clips.extend(clips)

    # Deduplicate in case overlapping chunks caused duplicate discoveries
    unique_texts = set()
    deduped_clips = []
    for clip in all_candidate_clips:
        text = clip.get("clip_text") if isinstance(clip, dict) else getattr(clip, "clip_text", "")
        if text and text not in unique_texts:
            unique_texts.add(text)
            deduped_clips.append(clip)

    # Sort clips descending by virality score
    def get_score(x):
        return x.get("virality_score", 0.0) if isinstance(x, dict) else getattr(x, "virality_score", 0.0)
        
    deduped_clips.sort(key=get_score, reverse=True)

    # Return up to 10 sorted clips 
    final_clips = deduped_clips[:10]

    logger.info(f"Discovered {len(final_clips)} candidate clips concurrently across {len(batches)} batches")
    return ClipDiscoveryOutput(clips=final_clips)
