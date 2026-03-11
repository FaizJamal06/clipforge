"""
ClipForge AI — Clip Discovery Agent

Uses LLM to analyze transcript chunks and identify the most viral
40-60 second segments. Each selected clip must be verbatim, continuous,
and contain a strong hook + payoff structure.
"""

import json
import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ----- Structured Output Schema ----- #

class DiscoveredClip(BaseModel):
    """Schema for a single discovered clip candidate."""
    clip_text: str = Field(description="Exact verbatim text from the transcript.")
    start_time: float = Field(description="Estimated start timestamp in seconds.")
    end_time: float = Field(description="Estimated end timestamp in seconds.")
    duration: float = Field(description="Clip duration in seconds (should be 40-60).")
    virality_reasoning: str = Field(description="Explanation of why this clip is likely to go viral.")
    hook: str = Field(description="The opening hook that grabs attention.")
    payoff: str = Field(description="The satisfying conclusion or punchline.")


class ClipDiscoveryOutput(BaseModel):
    """Schema for the clip discovery agent output."""
    clips: list[DiscoveredClip] = Field(description="Top 3 viral clip candidates, ranked by virality.")


# ----- Prompt Template ----- #

CLIP_DISCOVERY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert viral content strategist specializing in short-form podcast clips.

Your task is to analyze a podcast transcript and identify the TOP 3 most viral 40-60 second segments.

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

Rank clips by virality potential. Explain your reasoning for each selection.
The clip_text must be COPIED EXACTLY from the transcript text — character for character.""",
    ),
    (
        "human",
        """Analyze the following podcast transcript and identify the top 3 viral clips (40-60 seconds each).

<transcript>
{transcript_chunks}
</transcript>

Return exactly 3 clips as structured output with verbatim text, timestamps, duration, and virality reasoning.""",
    ),
])


# ----- Agent Logic ----- #

async def run(transcript_chunks: list[str], llm: ChatOpenAI) -> ClipDiscoveryOutput:
    """Execute the clip discovery agent.

    Invokes the LLM with the discovery prompt and forces structured output.

    Args:
        transcript_chunks: Processed transcript chunks to analyze.
        llm: LangChain ChatOpenAI instance.

    Returns:
        ClipDiscoveryOutput with top 3 viral clip candidates.

    Raises:
        Exception: If LLM call fails after retries.
    """
    # Join all chunks with separators for context
    combined_transcript = "\n\n---\n\n".join(transcript_chunks)

    # Build the chain with structured output
    structured_llm = llm.with_structured_output(ClipDiscoveryOutput)
    chain = CLIP_DISCOVERY_PROMPT | structured_llm

    logger.info(f"Running clip discovery on {len(transcript_chunks)} chunks...")

    result = await chain.ainvoke({"transcript_chunks": combined_transcript})

    logger.info(f"Discovered {len(result.clips)} candidate clips")
    return result
