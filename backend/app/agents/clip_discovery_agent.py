"""
ClipForge AI — Clip Discovery Agent

Uses LLM to analyze transcript chunks and identify the most viral
40-60 second segments. Each selected clip must be verbatim, continuous,
and contain a strong hook + payoff structure.

This is a SCAFFOLD — placeholder logic only.
Full implementation will be added in the execution phase.
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


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
3. Each clip MUST be 40-60 seconds in duration.
4. Each clip MUST contain a strong HOOK (attention-grabbing opening) and a PAYOFF (satisfying conclusion).

VIRAL CRITERIA:
- Emotional peaks (surprise, humor, outrage, awe)
- Curiosity gaps (statements that make viewers need to hear more)
- Contrarian or controversial takes
- Personal stories with universal resonance
- "Quotable" moments that stand alone without context

Rank clips by virality potential. Explain your reasoning for each selection.""",
    ),
    (
        "human",
        """Analyze the following podcast transcript and identify the top 3 viral clips.

<transcript>
{transcript_chunks}
</transcript>

Return the clips as structured output with verbatim text, timestamps, duration, and virality reasoning.""",
    ),
])


# ----- Agent Logic ----- #

async def run(transcript_chunks: list[str], llm=None) -> ClipDiscoveryOutput:
    """Execute the clip discovery agent.

    Args:
        transcript_chunks: Processed transcript chunks to analyze.
        llm: LangChain LLM instance (injected via dependency).

    Returns:
        ClipDiscoveryOutput with top 3 viral clip candidates.

    TODO: Implement actual LLM call with structured output.
    """
    # Placeholder response
    return ClipDiscoveryOutput(
        clips=[
            DiscoveredClip(
                clip_text="[Placeholder] This is where the verbatim clip text would appear...",
                start_time=120.0,
                end_time=165.0,
                duration=45.0,
                virality_reasoning="Placeholder — will be filled by LLM analysis.",
                hook="Placeholder hook",
                payoff="Placeholder payoff",
            )
        ]
    )
