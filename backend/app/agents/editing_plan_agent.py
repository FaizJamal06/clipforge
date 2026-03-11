"""
ClipForge AI — Editing Plan Agent

Generates a professional editing blueprint for each validated clip.
Includes timestamps, B-roll suggestions, caption strategy, and pacing instructions.
"""

import logging
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ----- Structured Output Schema ----- #

class EditingSegment(BaseModel):
    """A single segment within the editing plan timeline."""
    timestamp: str = Field(description="Timestamp range for this segment (e.g., '0:00-0:05').")
    visual_type: str = Field(description="Type of visual (e.g., 'talking_head', 'broll', 'text_overlay').")
    broll_idea: str = Field(default="", description="B-roll suggestion for this segment.")
    caption_text: str = Field(default="", description="Caption/subtitle text for this segment.")
    editing_note: str = Field(default="", description="Pacing or editing instruction.")


class ClipEditingPlan(BaseModel):
    """Complete editing plan for a single clip."""
    clip_index: int = Field(description="Index of the clip this plan is for.")
    title_suggestion: str = Field(description="Suggested title for the short-form clip.")
    hook_strategy: str = Field(description="How to visually emphasize the opening hook.")
    segments: list[EditingSegment] = Field(description="Timeline of editing segments.")
    caption_style: str = Field(description="Overall caption style recommendation.")
    pacing_notes: str = Field(description="General pacing and rhythm instructions.")
    call_to_action: str = Field(description="Recommended CTA for the end of the clip.")


class EditingPlanOutput(BaseModel):
    """Schema for the editing plan agent output."""
    plans: list[ClipEditingPlan] = Field(description="Editing plans for each validated clip.")


# ----- Prompt Template ----- #

EDITING_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a professional short-form video editor and content strategist.

Your task is to create a detailed editing blueprint for podcast clips that will be
published as short-form content (TikTok, Reels, YouTube Shorts).

For each clip, generate:
1. TITLE SUGGESTION: A compelling, scroll-stopping title (max 60 characters).
2. HOOK STRATEGY: How to visually emphasize the opening 3-5 seconds to prevent scroll-past.
3. SEGMENT TIMELINE: Break the clip into 5-10 second segments with:
   - Visual type (talking_head, broll, text_overlay, zoom, split_screen)
   - B-roll ideas (specific, relevant stock footage or graphics suggestions)
   - Caption text (key phrases for subtitles — punchy, engaging)
   - Editing notes (cuts, transitions, pacing, zoom intensity)
4. CAPTION STYLE: Overall subtitle design recommendation (font, color, placement, animation).
5. PACING NOTES: Rhythm, energy curve, where to speed up/slow down.
6. CALL TO ACTION: What viewers should do after watching (follow, comment, share).

Think like a viral content creator. Every decision should maximize engagement and watch time.
Match the clip_index to the index of the input clip.""",
    ),
    (
        "human",
        """Create editing plans for the following validated podcast clips:

<clips>
{validated_clips}
</clips>

Generate a detailed, actionable editing blueprint for each clip.""",
    ),
])


# ----- Agent Logic ----- #

async def generate(validated_clips: list[dict], llm: ChatOpenAI) -> EditingPlanOutput:
    """Execute the editing plan agent.

    Invokes the LLM with the editing plan prompt and forces structured output.

    Args:
        validated_clips: Validated clips to generate editing plans for.
        llm: LangChain ChatOpenAI instance.

    Returns:
        EditingPlanOutput with editing plans for each clip.

    Raises:
        Exception: If LLM call fails after retries.
    """
    import json

    # Format clips for the prompt
    clips_text = json.dumps(validated_clips, indent=2)

    # Build the chain with structured output
    structured_llm = llm.with_structured_output(EditingPlanOutput)
    chain = EDITING_PLAN_PROMPT | structured_llm

    logger.info(f"Generating editing plans for {len(validated_clips)} clips...")

    result = await chain.ainvoke({"validated_clips": clips_text})

    logger.info(f"Generated {len(result.plans)} editing plans")
    return result
