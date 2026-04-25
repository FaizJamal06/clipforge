"""
ClipForge AI — Adaptive Rate Limiter

A centralized, pipeline-wide rate limiter for LLM API calls.
Uses a sliding-window approach to stay within Gemini free-tier quotas
(5 requests/minute) while minimizing total pipeline latency.

All agents share a single limiter instance so the quota is respected
globally across clip discovery, validation, and editing plan stages.
"""

import asyncio
import time
import logging
from collections import deque

logger = logging.getLogger(__name__)


class AdaptiveRateLimiter:
    """Sliding-window rate limiter with adaptive back-off.

    Instead of spacing requests evenly (which wastes time when the window
    is clear), this limiter tracks actual request timestamps and only
    sleeps when the next request would exceed the quota.

    Features:
        - Minimal delay when the window is clear (burst-friendly)
        - Respects per-minute quota across the entire pipeline
        - Adaptive back-off when 429 errors are encountered
        - Thread/task-safe via asyncio.Lock

    Attributes:
        max_requests: Maximum requests allowed per window.
        window_seconds: Duration of the sliding window in seconds.
    """

    def __init__(self, max_requests: int = 4, window_seconds: float = 60.0):
        """Initialize the rate limiter.

        Args:
            max_requests: Max requests per window. Defaults to 4 (under the
                          free-tier limit of 5 to leave headroom for retries).
            window_seconds: Window duration in seconds.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._backoff_until: float = 0.0  # Adaptive back-off deadline

    async def acquire(self, label: str = "") -> None:
        """Wait until a request slot is available, then claim it.

        Args:
            label: Optional label for logging (e.g., "discovery batch 3").
        """
        async with self._lock:
            now = time.monotonic()

            # Honour any active back-off from a previous 429 error
            if now < self._backoff_until:
                wait = self._backoff_until - now
                tag = f" [{label}]" if label else ""
                logger.info(f"Rate limiter{tag}: back-off wait {wait:.1f}s")
                await asyncio.sleep(wait)
                now = time.monotonic()

            # Purge timestamps outside the current window
            while self._timestamps and self._timestamps[0] <= now - self.window_seconds:
                self._timestamps.popleft()

            # If window is full, sleep until the oldest request expires
            if len(self._timestamps) >= self.max_requests:
                oldest = self._timestamps[0]
                wait = (oldest + self.window_seconds) - now + 0.5  # +0.5s safety margin
                if wait > 0:
                    tag = f" [{label}]" if label else ""
                    logger.info(
                        f"Rate limiter{tag}: window full ({len(self._timestamps)}/{self.max_requests}), "
                        f"waiting {wait:.1f}s"
                    )
                    await asyncio.sleep(wait)
                    now = time.monotonic()

                    # Re-purge after sleeping
                    while self._timestamps and self._timestamps[0] <= now - self.window_seconds:
                        self._timestamps.popleft()

            # Record this request
            self._timestamps.append(now)
            tag = f" [{label}]" if label else ""
            logger.debug(
                f"Rate limiter{tag}: slot acquired ({len(self._timestamps)}/{self.max_requests} used)"
            )

    def report_rate_limit_error(self, retry_after: float = 0) -> None:
        """Call this when a 429 is received to trigger adaptive back-off.

        Args:
            retry_after: Seconds to wait (from the API error). Falls back
                         to 15s if not provided.
        """
        wait = max(retry_after, 15.0)
        self._backoff_until = time.monotonic() + wait
        logger.warning(f"Rate limiter: 429 received, back-off for {wait:.0f}s")


# ---------------------------------------------------------------------------
# Singleton — shared across all agents in the pipeline
# ---------------------------------------------------------------------------

_global_limiter: AdaptiveRateLimiter | None = None


def get_rate_limiter() -> AdaptiveRateLimiter:
    """Return the global rate limiter instance (created on first call).

    Reads max_requests from settings.llm_rate_limit_rpm.
    """
    global _global_limiter
    if _global_limiter is None:
        from app.config import get_settings
        settings = get_settings()
        _global_limiter = AdaptiveRateLimiter(
            max_requests=settings.llm_rate_limit_rpm,
            window_seconds=60.0,
        )
        logger.info(f"Rate limiter initialized: {settings.llm_rate_limit_rpm} req/min")
    return _global_limiter
