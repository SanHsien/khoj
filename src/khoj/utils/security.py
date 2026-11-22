from __future__ import annotations

from collections.abc import Mapping
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


LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "[::1]")
# Starlette's TestClient sends "Host: testserver". It is not a resolvable name, so a
# rebinding page cannot make a browser send it, and the product test suite needs it.
TEST_CLIENT_HOST = "testserver"


def trusted_hosts(env: Mapping[str, str]) -> list[str]:
    """Host header values the FastAPI server accepts (DNS-rebinding defense).

    A rebinding page reaches the server under an attacker-controlled name, so the Host
    header is the one thing it cannot fake. Loopback names always work. The deployment
    domain follows the same variables Django's ALLOWED_HOSTS uses: KHOJ_DOMAIN, and
    KHOJ_ALLOWED_DOMAIN when set (a reverse proxy or docker service name). Subdomains
    are allowed, as in Django. KHOJ_TRUSTED_HOSTS adds comma separated extras; "*"
    turns the check off.
    """
    hosts = [*LOOPBACK_HOSTS, TEST_CLIENT_HOST]
    domain = (env.get("KHOJ_DOMAIN") or "").strip()
    allowed_domain = (env.get("KHOJ_ALLOWED_DOMAIN") or domain).strip()
    for name in (domain, allowed_domain):
        if name:
            hosts += [name, f"*.{name}"]
    hosts += [item.strip() for item in (env.get("KHOJ_TRUSTED_HOSTS") or "").split(",") if item.strip()]
    return list(dict.fromkeys(hosts))
