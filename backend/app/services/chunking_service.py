"""
ClipForge AI — Chunking Service

Handles transcript cleaning, segment merging, and timestamp-aware chunking.
Preserves timestamps throughout processing for accurate clip mapping.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Common filler words to remove from transcripts
FILLER_WORDS = {
    "um", "uh", "uhh", "umm", "hmm", "hm",
    "like,", "you know,", "i mean,",  # only with trailing comma to avoid false positives
}


def clean_transcript_text(text: str) -> str:
    """Clean raw transcript text.

    - Normalizes whitespace
    - Removes common filler sounds (um, uh, hmm)
    - Fixes double punctuation
    - Strips leading/trailing whitespace

    Args:
        text: Raw transcript text to clean.

    Returns:
        Cleaned transcript text.
    """
    if not text:
        return ""

    # Normalize whitespace
    cleaned = " ".join(text.split())

    # Remove standalone filler sounds (case-insensitive, word-boundary)
    cleaned = re.sub(r'\b(?:um|uh|uhh|umm|hmm|hm)\b', '', cleaned, flags=re.IGNORECASE)

    # Clean up double spaces left by filler removal
    cleaned = re.sub(r'\s{2,}', ' ', cleaned)

    # Fix double punctuation
    cleaned = re.sub(r'([.!?])\s*\1+', r'\1', cleaned)

    return cleaned.strip()


def merge_segments(segments: list[dict], max_gap: float = 1.5) -> list[dict]:
    """Merge transcript segments that are close together.

    YouTube transcripts often have very short segments (1-2 words).
    This merges adjacent segments into coherent sentences while
    preserving accurate timestamps.

    Args:
        segments: Raw transcript segments with text, start, duration.
        max_gap: Maximum gap in seconds between segments to merge.

    Returns:
        Merged segments list with keys: text, start, end, duration.
    """
    if not segments:
        return []

    merged = []
    current = {
        "text": segments[0].get("text", ""),
        "start": segments[0].get("start", 0.0),
        "duration": segments[0].get("duration", 0.0),
    }
    current["end"] = current["start"] + current["duration"]

    for seg in segments[1:]:
        seg_start = seg.get("start", 0.0)
        seg_duration = seg.get("duration", 0.0)
        seg_end = seg_start + seg_duration
        seg_text = seg.get("text", "")

        # Calculate gap between current segment end and next segment start
        gap = seg_start - current["end"]

        if gap <= max_gap:
            # Merge: extend current segment
            current["text"] = current["text"] + " " + seg_text
            current["end"] = seg_end
            current["duration"] = current["end"] - current["start"]
        else:
            # Gap too large: finalize current and start new
            merged.append(current)
            current = {
                "text": seg_text,
                "start": seg_start,
                "end": seg_end,
                "duration": seg_duration,
            }

    # Don't forget the last segment
    merged.append(current)

    logger.info(f"Merged {len(segments)} segments → {len(merged)} segments")
    return merged


def _format_timestamp(seconds: float) -> str:
    """Format seconds into MM:SS or H:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def chunk_transcript(
    segments: list[dict],
    chunk_duration: float = 300.0,
    overlap_duration: float = 30.0,
) -> list[str]:
    """Chunk transcript into manageable segments for LLM analysis.

    Creates overlapping chunks to ensure no viral moments are split
    across chunk boundaries. Each chunk includes timestamp markers.

    Args:
        segments: Merged transcript segments (must have start, end, text).
        chunk_duration: Target duration per chunk in seconds (default: 5 minutes).
        overlap_duration: Overlap between chunks in seconds (default: 30 seconds).

    Returns:
        List of chunk text strings with timestamp annotations.
    """
    if not segments:
        return []

    # If total duration fits in one chunk, return as a single chunk
    total_start = segments[0].get("start", 0.0)
    total_end = segments[-1].get("end", segments[-1].get("start", 0) + segments[-1].get("duration", 0))
    total_duration = total_end - total_start

    if total_duration <= chunk_duration:
        # Single chunk — include all segments with timestamps
        chunk_text = _build_chunk_text(segments)
        return [chunk_text] if chunk_text.strip() else []

    # Multi-chunk: slide window with overlap
    chunks = []
    chunk_start_time = total_start

    while chunk_start_time < total_end:
        chunk_end_time = chunk_start_time + chunk_duration

        # Collect segments that fall within this chunk window
        chunk_segments = [
            seg for seg in segments
            if seg.get("start", 0) < chunk_end_time
            and seg.get("end", seg.get("start", 0) + seg.get("duration", 0)) > chunk_start_time
        ]

        if chunk_segments:
            chunk_text = _build_chunk_text(chunk_segments)
            if chunk_text.strip():
                chunks.append(chunk_text)

        # Advance window with overlap
        chunk_start_time += (chunk_duration - overlap_duration)

    logger.info(
        f"Chunked transcript ({total_duration:.0f}s) into {len(chunks)} chunks "
        f"(target: {chunk_duration}s, overlap: {overlap_duration}s)"
    )
    return chunks


def _build_chunk_text(segments: list[dict]) -> str:
    """Build chunk text from segments with timestamp markers.

    Format: [MM:SS] Transcript text here...

    Args:
        segments: Segments to include in this chunk.

    Returns:
        Formatted chunk text string.
    """
    lines = []
    for seg in segments:
        timestamp = _format_timestamp(seg.get("start", 0.0))
        text = seg.get("text", "").strip()
        if text:
            lines.append(f"[{timestamp}] {text}")
    return "\n".join(lines)


def process_transcript(raw_segments: list[dict]) -> list[str]:
    """Full transcript processing pipeline.

    Runs: clean → merge → chunk.

    Args:
        raw_segments: Raw transcript segments from YouTube.

    Returns:
        List of processed, chunked transcript strings with timestamp annotations.
    """
    if not raw_segments:
        return []

    # Step 1: Clean each segment's text
    cleaned = [
        {**seg, "text": clean_transcript_text(seg.get("text", ""))}
        for seg in raw_segments
    ]

    # Remove empty segments after cleaning
    cleaned = [seg for seg in cleaned if seg.get("text", "").strip()]

    if not cleaned:
        return []

    # Step 2: Merge short segments
    merged = merge_segments(cleaned)

    # Step 3: Chunk for LLM processing
    chunks = chunk_transcript(merged)

    logger.info(f"Processed {len(raw_segments)} raw segments → {len(chunks)} chunks")
    return chunks


def get_full_transcript_text(segments: list[dict]) -> str:
    """Get the full transcript as a single text string.

    Used for validation (checking if clip text exists in transcript).

    Args:
        segments: Raw or merged transcript segments.

    Returns:
        Full transcript text as a single string.
    """
    return " ".join(seg.get("text", "") for seg in segments).strip()
