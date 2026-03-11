"""
ClipForge AI — API Routes

REST endpoints for the ClipForge pipeline.
The frontend communicates with these endpoints to submit URLs
and retrieve processing results.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

router = APIRouter(tags=["clipforge"])


# ----- Request / Response Models ----- #

class ProcessRequest(BaseModel):
    """Request body for the /process endpoint."""
    youtube_url: str = Field(
        ...,
        description="YouTube video URL to extract clips from.",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    )


class ClipResult(BaseModel):
    """A single validated clip with its editing plan."""
    clip_text: str = Field(description="Verbatim clip transcript text.")
    start_time: float = Field(description="Clip start timestamp in seconds.")
    end_time: float = Field(description="Clip end timestamp in seconds.")
    duration: float = Field(description="Clip duration in seconds.")
    virality_score: float = Field(default=0.0, description="Virality score (0-10).")
    editing_plan: dict = Field(default_factory=dict, description="Editing blueprint for this clip.")


class ProcessResponse(BaseModel):
    """Response body for the /process endpoint."""
    status: str = Field(description="Processing status.")
    youtube_url: str = Field(description="Original input URL.")
    video_id: str = Field(description="Extracted YouTube video ID.")
    clips: list[ClipResult] = Field(default_factory=list, description="Validated clips with editing plans.")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered.")


# ----- Endpoints ----- #

@router.post("/process", response_model=ProcessResponse)
async def process_video(request: ProcessRequest):
    """Submit a YouTube URL for clip discovery and editing plan generation.

    This endpoint triggers the full LangGraph pipeline:
    1. Input validation & video ID extraction
    2. Transcript retrieval
    3. Transcript processing & chunking
    4. AI clip discovery
    5. Clip validation (with retry loop)
    6. Editing plan generation
    7. Output formatting

    TODO: Wire up the LangGraph pipeline execution.
    Currently returns a placeholder response.
    """
    # Placeholder response — will be replaced with actual pipeline execution
    return ProcessResponse(
        status="scaffold_placeholder",
        youtube_url=request.youtube_url,
        video_id="placeholder_id",
        clips=[],
        errors=["Pipeline not yet implemented — this is a scaffold response."],
    )


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of a processing job.

    TODO: Implement job tracking with database persistence.
    """
    raise HTTPException(
        status_code=501,
        detail="Job tracking not yet implemented — scaffold only.",
    )
