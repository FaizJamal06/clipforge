"""
ClipForge AI — Clip Validation Agent

Validates discovered clips against production rules:
1. Transcript containment — clip text must exist in original transcript.
2. Continuity — clip must be a continuous segment.
3. Duration — clip must be within 40-60 second range.
4. Hallucination detection — reject any LLM-fabricated text.

This is a SCAFFOLD — placeholder logic only.
Full implementation will be added in the execution phase.
"""

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


# ----- Structured Output Schema ----- #

class ValidationResult(BaseModel):
    """Schema for a single clip validation result."""
    clip_index: int = Field(description="Index of the clip being validated.")
    is_valid: bool = Field(description="Whether the clip passed all validation checks.")
    transcript_match: bool = Field(description="Whether clip text exists in the original transcript.")
    is_continuous: bool = Field(description="Whether the clip is a continuous segment.")
    duration_valid: bool = Field(description="Whether clip duration is within 40-60 seconds.")
    no_hallucination: bool = Field(description="Whether the clip contains no fabricated text.")
    failure_reasons: list[str] = Field(default_factory=list, description="Reasons for validation failure.")


class ClipValidationOutput(BaseModel):
    """Schema for the validation agent output."""
    results: list[ValidationResult] = Field(description="Validation results for each clip.")
    all_passed: bool = Field(description="Whether all clips passed validation.")


# ----- Prompt Template ----- #

CLIP_VALIDATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a quality assurance agent for a podcast clipping system.

Your task is to validate AI-generated clip selections against strict production rules.

VALIDATION RULES:
1. TRANSCRIPT CONTAINMENT: The clip text must appear EXACTLY in the original transcript. 
   Character-for-character match required.
2. CONTINUITY: The clip must be a single continuous segment from the transcript.
   It cannot be spliced from multiple non-adjacent sections.
3. DURATION: The clip must be between 40-60 seconds in length.
4. NO HALLUCINATION: Every word in the clip must come from the transcript.
   The LLM must not have added, modified, or rearranged any text.

For each clip, report whether it passes or fails each check.
If a clip fails, provide specific failure reasons.""",
    ),
    (
        "human",
        """Validate the following clips against the original transcript.

<original_transcript>
{transcript}
</original_transcript>

<clips_to_validate>
{candidate_clips}
</clips_to_validate>

For each clip, check all 4 validation rules and report results.""",
    ),
])


# ----- Agent Logic ----- #

async def validate(
    candidate_clips: list[dict],
    transcript: list[dict],
    llm=None,
) -> ClipValidationOutput:
    """Execute the clip validation agent.

    Args:
        candidate_clips: Clips to validate.
        transcript: Original transcript for containment checks.
        llm: LangChain LLM instance (injected via dependency).

    Returns:
        ClipValidationOutput with validation results for each clip.

    TODO: Implement actual validation logic (exact match, fuzzy match, duration check).
    """
    # Placeholder: all clips pass validation
    results = [
        ValidationResult(
            clip_index=i,
            is_valid=True,
            transcript_match=True,
            is_continuous=True,
            duration_valid=True,
            no_hallucination=True,
            failure_reasons=[],
        )
        for i in range(len(candidate_clips))
    ]

    return ClipValidationOutput(
        results=results,
        all_passed=True,
    )
