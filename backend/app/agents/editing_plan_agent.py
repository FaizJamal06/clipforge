"""
ClipForge AI — Editing Plan Agent

Generates a professional editing blueprint for each validated clip.
Includes timestamps, B-roll suggestions, caption strategy, and pacing instructions.

This is a SCAFFOLD — placeholder logic only.
Full implementation will be added in the execution phase.
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


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
1. TITLE SUGGESTION: A compelling, scroll-stopping title.
2. HOOK STRATEGY: How to visually emphasize the opening 3-5 seconds.
3. SEGMENT TIMELINE: Break the clip into 5-10 second segments with:
   - Visual type (talking head, B-roll, text overlay, zoom)
   - B-roll ideas (relevant stock footage or graphics)
   - Caption text (engaging subtitles)
   - Editing notes (cuts, transitions, pacing)
4. CAPTION STYLE: Overall subtitle design recommendation.
5. PACING NOTES: Rhythm, energy, and flow instructions.
6. CALL TO ACTION: What viewers should do after watching.

Think like a viral content creator. Every decision should maximize engagement.""",
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

async def generate(validated_clips: list[dict], llm=None) -> EditingPlanOutput:
    """Execute the editing plan agent.

    Args:
        validated_clips: Validated clips to generate editing plans for.
        llm: LangChain LLM instance (injected via dependency).

    Returns:
        EditingPlanOutput with editing plans for each clip.

    TODO: Implement actual LLM call with structured output.
    """
    # Placeholder editing plans
    plans = [
        ClipEditingPlan(
            clip_index=i,
            title_suggestion="[Placeholder] Viral Clip Title",
            hook_strategy="[Placeholder] Open with dramatic zoom on speaker's face.",
            segments=[
                EditingSegment(
                    timestamp="0:00-0:05",
                    visual_type="talking_head",
                    broll_idea="",
                    caption_text="[Hook text placeholder]",
                    editing_note="Quick zoom in, dramatic pause.",
                ),
            ],
            caption_style="Bold white text with black outline, centered bottom third.",
            pacing_notes="[Placeholder] Fast cuts for the first 10 seconds, then let the story breathe.",
            call_to_action="Follow for more moments like this.",
        )
        for i in range(len(validated_clips))
    ]

    return EditingPlanOutput(plans=plans)
