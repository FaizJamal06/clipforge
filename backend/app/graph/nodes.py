"""
ClipForge AI — LangGraph Node Functions

Each function is a node in the LangGraph pipeline.
Nodes receive the current state and return a dict of state updates.

Pipeline order:
    InputHandler → TranscriptRetrieval → TranscriptProcessing →
    ClipDiscovery → ClipValidation → EditingPlan → OutputFormatter
                         ↑                  |
                         └── retry loop ─────┘
"""

import logging

from app.graph.state import ClipForgeState
from app.services.transcript_service import (
    validate_youtube_url,
    fetch_transcript,
    TranscriptError,
)
from app.services.chunking_service import process_transcript, get_full_transcript_text
from app.agents import clip_discovery_agent, clip_validation_agent, editing_plan_agent
from app.dependencies import get_llm_client

logger = logging.getLogger(__name__)


def input_handler(state: ClipForgeState) -> dict:
    """Node 1 — Input Handler

    Validates the YouTube URL and extracts the video ID.
    """
    youtube_url = state["youtube_url"]

    try:
        video_id = validate_youtube_url(youtube_url)
        logger.info(f"Input validated: video_id={video_id}")
        return {
            "video_id": video_id,
            "status": "input_validated",
            "errors": [],
        }
    except TranscriptError as e:
        logger.error(f"Input validation failed: {e}")
        return {
            "video_id": "",
            "status": "failed",
            "errors": [str(e)],
        }


def transcript_retrieval(state: ClipForgeState) -> dict:
    """Node 2 — Transcript Retrieval

    Fetches the full transcript from YouTube using youtube-transcript-api.
    """
    video_id = state.get("video_id", "")

    if not video_id:
        return {
            "transcript": [],
            "status": "failed",
            "errors": state.get("errors", []) + ["No video ID available — skipping transcript retrieval."],
        }

    try:
        # Synchronous call (youtube-transcript-api is sync)
        transcript = fetch_transcript(video_id)
        logger.info(f"Retrieved {len(transcript)} transcript segments for {video_id}")
        return {
            "transcript": transcript,
            "status": "transcript_retrieved",
        }
    except TranscriptError as e:
        logger.error(f"Transcript retrieval failed: {e}")
        return {
            "transcript": [],
            "status": "failed",
            "errors": state.get("errors", []) + [str(e)],
        }


def transcript_processing(state: ClipForgeState) -> dict:
    """Node 3 — Transcript Processing

    Cleans, merges speaker segments, and chunks the transcript.
    """
    transcript = state.get("transcript", [])

    if not transcript:
        return {
            "transcript_chunks": [],
            "status": "failed",
            "errors": state.get("errors", []) + ["No transcript available — skipping processing."],
        }

    try:
        chunks = process_transcript(transcript)
        logger.info(f"Processed transcript into {len(chunks)} chunks")
        return {
            "transcript_chunks": chunks,
            "status": "transcript_processed",
        }
    except Exception as e:
        logger.error(f"Transcript processing failed: {e}")
        return {
            "transcript_chunks": [],
            "status": "failed",
            "errors": state.get("errors", []) + [f"Transcript processing error: {str(e)}"],
        }


async def clip_discovery(state: ClipForgeState) -> dict:
    """Node 4 — Clip Discovery Agent

    Analyzes transcript chunks using LLM to identify viral clips.
    """
    transcript_chunks = state.get("transcript_chunks", [])

    if not transcript_chunks:
        return {
            "candidate_clips": [],
            "status": "failed",
            "errors": state.get("errors", []) + ["No transcript chunks available — skipping discovery."],
        }

    try:
        llm = get_llm_client()
        result = await clip_discovery_agent.run(transcript_chunks, llm)

        # Convert Pydantic models to dicts for state
        candidate_clips = [clip.model_dump() for clip in result.clips]
        logger.info(f"Discovered {len(candidate_clips)} candidate clips")

        return {
            "candidate_clips": candidate_clips,
            "status": "clips_discovered",
        }
    except ValueError as e:
        # LLM key not configured
        logger.error(f"LLM configuration error: {e}")
        return {
            "candidate_clips": [],
            "status": "failed",
            "errors": state.get("errors", []) + [str(e)],
        }
    except Exception as e:
        logger.error(f"Clip discovery failed: {e}")
        return {
            "candidate_clips": [],
            "status": "failed",
            "errors": state.get("errors", []) + [f"Clip discovery error: {str(e)}"],
        }


async def clip_validation(state: ClipForgeState) -> dict:
    """Node 5 — Clip Validation Agent

    Validates each candidate clip using programmatic checks.
    Increments retry_count on failure for the conditional loop.
    """
    candidate_clips = state.get("candidate_clips", [])
    transcript = state.get("transcript", [])
    retry_count = state.get("retry_count", 0)

    if not candidate_clips:
        return {
            "validated_clips": [],
            "failed_clips": [],
            "retry_count": retry_count,
            "status": "clips_validated",
        }

    try:
        llm = get_llm_client()
    except ValueError:
        llm = None

    try:
        result = await clip_validation_agent.validate(candidate_clips, transcript, llm)

        validated = []
        failed = []

        for vr in result.results:
            clip = candidate_clips[vr.clip_index] if vr.clip_index < len(candidate_clips) else {}
            if vr.is_valid:
                validated.append({**clip, "match_score": vr.match_score})
            else:
                failed.append({
                    **clip,
                    "match_score": vr.match_score,
                    "failure_reasons": vr.failure_reasons,
                })

        # Increment retry count if any clips failed
        new_retry_count = retry_count + 1 if failed and not validated else retry_count

        logger.info(f"Validation: {len(validated)} passed, {len(failed)} failed (retry #{retry_count})")

        return {
            "validated_clips": validated,
            "failed_clips": failed,
            "retry_count": new_retry_count,
            "status": "clips_validated",
        }
    except Exception as e:
        logger.error(f"Clip validation failed: {e}")
        # On validation error, pass clips through (graceful degradation)
        return {
            "validated_clips": candidate_clips,
            "failed_clips": [],
            "retry_count": retry_count,
            "status": "clips_validated",
            "errors": state.get("errors", []) + [f"Validation warning: {str(e)}"],
        }


async def editing_plan(state: ClipForgeState) -> dict:
    """Node 6 — Editing Plan Agent

    Generates editing blueprints for validated clips using LLM.
    """
    validated_clips = state.get("validated_clips", [])

    if not validated_clips:
        return {
            "editing_plans": [],
            "status": "editing_plans_generated",
        }

    try:
        llm = get_llm_client()
        result = await editing_plan_agent.generate(validated_clips, llm)

        # Convert Pydantic models to dicts
        plans = [plan.model_dump() for plan in result.plans]
        logger.info(f"Generated {len(plans)} editing plans")

        return {
            "editing_plans": plans,
            "status": "editing_plans_generated",
        }
    except ValueError as e:
        logger.error(f"LLM configuration error: {e}")
        return {
            "editing_plans": [],
            "status": "editing_plans_generated",
            "errors": state.get("errors", []) + [f"Editing plan skipped: {str(e)}"],
        }
    except Exception as e:
        logger.error(f"Editing plan generation failed: {e}")
        return {
            "editing_plans": [],
            "status": "editing_plans_generated",
            "errors": state.get("errors", []) + [f"Editing plan error: {str(e)}"],
        }


def output_formatter(state: ClipForgeState) -> dict:
    """Node 7 — Output Formatter

    Merges validated clips with their editing plans into final output.
    """
    validated_clips = state.get("validated_clips", [])
    editing_plans = state.get("editing_plans", [])

    # Pair clips with their editing plans
    for i, clip in enumerate(validated_clips):
        matching_plans = [p for p in editing_plans if p.get("clip_index") == i]
        if matching_plans:
            clip["editing_plan"] = matching_plans[0]

    final_status = "completed" if validated_clips else "completed_no_clips"
    logger.info(f"Output formatted: {len(validated_clips)} clips with editing plans")

    return {
        "status": final_status,
    }
