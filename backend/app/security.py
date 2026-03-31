"""
ClipForge AI — Security Module

Provides prompt injection protection, input sanitization, and error
sanitization to defend against common attack vectors.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt Injection Guard
# ---------------------------------------------------------------------------

# Patterns that indicate prompt injection attempts (case-insensitive)
_INJECTION_PATTERNS = [
    # Direct instruction overrides
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"override\s+(all\s+)?previous",
    r"new\s+instructions?\s*:",
    # Role hijacking
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+(a\s+)?",
    r"pretend\s+(to\s+be|you\s+are)",
    r"system\s*:\s*",
    r"<\s*system\s*>",
    r"\[system\]",
    r"\[INST\]",
    r"<<\s*SYS\s*>>",
    # Data exfiltration
    r"reveal\s+(your|the)\s+(system|secret|api|internal)",
    r"show\s+me\s+(your|the)\s+prompt",
    r"what\s+(is|are)\s+your\s+instructions",
    r"repeat\s+(your|the)\s+(system|initial)\s+prompt",
    r"output\s+(your|the)\s+(system|initial)\s+prompt",
    # Encoded/obfuscated injections
    r"base64\s*:",
    r"eval\s*\(",
    r"exec\s*\(",
    r"\\x[0-9a-fA-F]{2}",  # hex-encoded chars
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


class PromptInjectionGuard:
    """Detects and neutralizes prompt injection attempts in text."""

    @staticmethod
    def scan(text: str) -> list[str]:
        """Scan text for prompt injection patterns.

        Args:
            text: Text to scan.

        Returns:
            List of matched pattern descriptions. Empty if clean.
        """
        if not text:
            return []

        matches = []
        for pattern in _COMPILED_PATTERNS:
            if pattern.search(text):
                matches.append(pattern.pattern)

        if matches:
            logger.warning(
                f"Prompt injection detected: {len(matches)} pattern(s) matched. "
                f"First match: {matches[0]}"
            )

        return matches

    @staticmethod
    def sanitize(text: str) -> str:
        """Remove or neutralize prompt injection patterns from text.

        Replaces dangerous patterns with harmless placeholders so the
        text structure is preserved but injection payloads are defused.

        Args:
            text: Text to sanitize.

        Returns:
            Sanitized text.
        """
        if not text:
            return text

        sanitized = text

        for pattern in _COMPILED_PATTERNS:
            sanitized = pattern.sub("[REDACTED]", sanitized)

        # Strip any remaining XML/HTML-like tags that could be prompt delimiters
        sanitized = re.sub(r"<\s*/?\s*(system|instruction|prompt|admin)\s*>", "[REDACTED]", sanitized, flags=re.IGNORECASE)

        if sanitized != text:
            logger.info("Sanitized potential prompt injection from input text")

        return sanitized

    @staticmethod
    def is_safe(text: str) -> bool:
        """Quick check if text is free of injection patterns.

        Args:
            text: Text to check.

        Returns:
            True if no injection patterns detected.
        """
        return len(PromptInjectionGuard.scan(text)) == 0


# ---------------------------------------------------------------------------
# Input Sanitizer
# ---------------------------------------------------------------------------

# Allowed characters in YouTube URLs
_URL_ALLOWLIST = re.compile(r"^[a-zA-Z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+$")

# Max URL length
MAX_URL_LENGTH = 500

# Max text input length (for any free-text field)
MAX_TEXT_LENGTH = 10000


class InputSanitizer:
    """Validates and sanitizes user inputs before processing."""

    @staticmethod
    def sanitize_url(url: str) -> str:
        """Validate and sanitize a YouTube URL.

        Args:
            url: Raw user-provided URL.

        Returns:
            Sanitized URL string.

        Raises:
            ValueError: If URL is invalid or suspicious.
        """
        if not url or not url.strip():
            raise ValueError("URL is empty.")

        url = url.strip()

        # Length check
        if len(url) > MAX_URL_LENGTH:
            raise ValueError(f"URL exceeds maximum length of {MAX_URL_LENGTH} characters.")

        # Character allowlist
        if not _URL_ALLOWLIST.match(url):
            raise ValueError("URL contains invalid characters.")

        # Scheme validation
        if not url.startswith(("https://", "http://")):
            raise ValueError("URL must use http:// or https:// scheme.")

        # Domain validation — must be YouTube
        url_lower = url.lower()
        valid_domains = ["youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com"]
        if not any(domain in url_lower for domain in valid_domains):
            raise ValueError("URL must be a YouTube domain.")

        # Strip control characters
        url = re.sub(r"[\x00-\x1f\x7f]", "", url)

        return url

    @staticmethod
    def sanitize_text(text: str, max_length: int = MAX_TEXT_LENGTH) -> str:
        """Sanitize free-text input.

        Args:
            text: Raw text input.
            max_length: Maximum allowed length.

        Returns:
            Sanitized text.

        Raises:
            ValueError: If text exceeds limits.
        """
        if not text:
            return ""

        if len(text) > max_length:
            raise ValueError(f"Text exceeds maximum length of {max_length} characters.")

        # Strip null bytes and control characters (keep newline, tab)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        return text


# ---------------------------------------------------------------------------
# Error Sanitizer
# ---------------------------------------------------------------------------

# Patterns that leak internal details
_ERROR_LEAK_PATTERNS = [
    re.compile(r"(?i)file\s+[\"']?[a-zA-Z]:\\\\", re.IGNORECASE),  # Windows paths
    re.compile(r"(?i)/home/|/usr/|/var/|/app/", re.IGNORECASE),  # Unix paths
    re.compile(r"line\s+\d+,?\s+in\s+\w+"),  # Stack trace lines
    re.compile(r"Traceback\s*\(most recent", re.IGNORECASE),  # Python traceback
    re.compile(r"at\s+0x[0-9a-fA-F]+"),  # Memory addresses
]


def sanitize_error(error: str | Exception) -> str:
    """Sanitize error messages to prevent information leakage.

    Strips file paths, stack traces, and internal details from error
    messages before they are returned to clients.

    Args:
        error: Error message or exception.

    Returns:
        Sanitized, user-safe error message.
    """
    msg = str(error)

    for pattern in _ERROR_LEAK_PATTERNS:
        if pattern.search(msg):
            logger.debug(f"Sanitized internal details from error message")
            return "An internal error occurred. Please try again later."

    # Truncate very long error messages
    if len(msg) > 500:
        msg = msg[:500] + "..."

    return msg
