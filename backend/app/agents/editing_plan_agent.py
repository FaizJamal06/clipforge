"""
ClipForge AI — Editing Plan Agent

Generates a professional editing blueprint for each validated clip.
Includes timestamps, B-roll suggestions, caption strategy, and pacing instructions.
"""

import logging
import asyncio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from app.security import PromptInjectionGuard

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
    pacing_notes: str | None = Field(default=None, description="General pacing and rhythm instructions.")
    call_to_action: str | None = Field(default=None, description="Recommended CTA for the end of the clip.")


class EditingPlanOutput(BaseModel):
    """Schema for the editing plan agent output."""
    plans: list[ClipEditingPlan] = Field(description="Editing plans for each validated clip.")


# ----- Prompt Template ----- #

EDITING_PLAN_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an expert viral content strategist, podcast clipper, and short-form video editor specializing in high-retention content for TikTok, Instagram Reels, and YouTube Shorts.

You specialize in turning long-form podcasts into viral short-form clips.

You deeply understand:
- Human psychology
- Short-form attention spans
- Curiosity gaps
- Pattern interrupts
- Retention loops
- Viral storytelling
- Visual storytelling through B-roll

--------------------------------------------------

TASK

You will be given a validated podcast clip segment.

Your job is to create a short-form editing plan using that exact segment, transformed into a viral editing plan.

Think like a professional viral short-form editor.
Use cinematic storytelling, pacing, and emotional visuals.

For each clip, populate the structured output with:
1. TITLE SUGGESTION: A compelling, scroll-stopping title (max 60 characters).
2. HOOK STRATEGY: A highly specific visual and auditory strategy to emphasize the opening 3-5 seconds and prevent scroll-past.
3. SEGMENT TIMELINE: Break the clip down into highly granular segments. For every segment, provide:
   - Visual type (Speaker / Cinematic B-roll / Mixed)
   - B-roll ideas (specific cinematic scene ideas)
   - Caption text (short, viral style)
   - Editing notes (zoom, cut, pacing, mood)
4. CAPTION STYLE: The subtitle design recommendation. Captions should be short, bold, and optimized for virality.
5. PACING NOTES: Include jump cuts, punch zooms, speed ramps, dramatic pauses, music tone, and emotional pacing.
6. CALL TO ACTION: A specific, creative CTA.

--------------------------------------------------

EDITING RULES

- Start with the SPEAKER for the hook.
- Use cinematic B-roll when the speaker describes:
  - emotions
  - situations
  - concepts
  - examples
- Return to the speaker for important insights or punchlines.
- Use B-roll to visualize ideas and maintain viewer retention.
- Keep pacing optimized for viral short-form content.
- Suggest realistic cinematic B-roll scenes that visually represent the message.

Think like a viral content creator. Every decision should maximize engagement and watch time.
Match the clip_index to the index of the input clip."""
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

async def generate(validated_clips: list[dict], llm: BaseChatModel) -> EditingPlanOutput:
    import json
    import re
    from app.rate_limiter import get_rate_limiter
    
    structured_llm = llm.with_structured_output(EditingPlanOutput)
    chain = EDITING_PLAN_PROMPT | structured_llm
    rate_limiter = get_rate_limiter()
    
    logger.info(f"Generating editing plans for {len(validated_clips)} clips individually...")
    
    editing_plans = []
    
    for i, clip in enumerate(validated_clips):
        label = f"editing plan {i + 1}/{len(validated_clips)}"
        # Sanitize clip data before sending to LLM
        clip_data = json.dumps([clip], indent=2)
        clip_data = PromptInjectionGuard.sanitize(clip_data)

        for attempt in range(3):
            try:
                await rate_limiter.acquire(label)
                result = await chain.ainvoke({"validated_clips": clip_data})
                if result and result.plans:
                    editing_plans.extend(result.plans)
                break  # Success
            except Exception as e:
                error_str = str(e)
                logger.error(f"Error in {label} (attempt {attempt+1}): {e}")

                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    match = re.search(r'retry in (\d+(?:\.\d+)?)s', error_str, re.IGNORECASE)
                    retry_after = float(match.group(1)) if match else 0
                    rate_limiter.report_rate_limit_error(retry_after)
                    wait = max(retry_after, 15.0) + 2
                    logger.info(f"{label}: rate limited, waiting {wait:.0f}s before retry")
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"{label}: failed after {attempt+1} attempt(s), "
                        f"clip will be missing from output. Error: {e}"
                    )
                    break  # Non-retryable error
        
    logger.info(f"Generated {len(editing_plans)} editing plans")
    return EditingPlanOutput(plans=editing_plans)

