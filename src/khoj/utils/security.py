from __future__ import annotations

from urllib.parse import urlsplit


def sanitize_log_value(value: object) -> str:
    """Render untrusted values on one physical log line."""
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def is_exact_https_host(url: str | None, expected_host: str) -> bool:
    """Return whether url uses HTTPS and exactly matches expected_host."""
    if not url:
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.hostname == expected_host
        and parsed.username is None
        and parsed.password is None
    )
