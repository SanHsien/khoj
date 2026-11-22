"""DNS-rebinding defense: the FastAPI app must refuse a Host header that is not ours.

Why: with --anonymous-mode there is no login, so a page that rebinds its own name to
127.0.0.1 could read and write every document from the victim's browser. The attacker
cannot change the Host header, which is why checking it stops the attack.

How: the host list is a pure function (`khoj.utils.security.trusted_hosts`); it is run
behind the real Starlette middleware here. `main.py` itself needs Django and torch, so a
separate test pins that it installs the middleware with that function.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.trustedhost import TrustedHostMiddleware  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from khoj.utils.security import trusted_hosts  # noqa: E402


def make_client(env: dict[str, str]) -> TestClient:
    app = FastAPI()

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts(env), www_redirect=False)
    return TestClient(app)


def status(client: TestClient, host: str) -> int:
    return client.get("/api/health", headers={"Host": host}).status_code


@pytest.mark.parametrize("host", ["localhost:42110", "127.0.0.1:42110", "[::1]:42110", "localhost"])
def test_loopback_hosts_are_served_with_no_configuration(host: str) -> None:
    assert status(make_client({}), host) == 200


@pytest.mark.parametrize("host", ["evil.example", "evil.example:42110", "127.0.0.1.evil.example", "localhost.evil.example"])
def test_rebound_attacker_hostname_gets_400(host: str) -> None:
    assert status(make_client({}), host) == 400


def test_configured_domain_and_its_subdomains_are_served_but_lookalikes_are_not() -> None:
    client = make_client({"KHOJ_DOMAIN": "khoj.example.com"})
    assert status(client, "khoj.example.com") == 200
    assert status(client, "app.khoj.example.com:443") == 200
    assert status(client, "khoj.example.com.evil.example") == 400
    assert status(client, "evilkhoj.example.com") == 400


def test_allowed_domain_for_a_reverse_proxy_or_docker_service_name_is_served() -> None:
    client = make_client({"KHOJ_DOMAIN": "khoj.example.com", "KHOJ_ALLOWED_DOMAIN": "server"})
    assert status(client, "server:42110") == 200
    assert status(client, "khoj.example.com") == 200


def test_ip_address_domain_is_served() -> None:
    assert status(make_client({"KHOJ_DOMAIN": "192.168.0.104"}), "192.168.0.104:42110") == 200


def test_extra_hosts_come_from_khoj_trusted_hosts_and_star_turns_the_check_off() -> None:
    assert status(make_client({"KHOJ_TRUSTED_HOSTS": "a.example, b.example"}), "b.example") == 200
    assert status(make_client({"KHOJ_TRUSTED_HOSTS": "*"}), "anything.example") == 200


def test_main_installs_the_middleware_with_the_env_derived_hosts() -> None:
    source = (ROOT / "src/khoj/main.py").read_text(encoding="utf-8")
    assert "app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts(os.environ)" in source
    # Added after CORS so it is outermost and runs first.
    assert source.index("add_middleware(\n    CORSMiddleware") < source.index("add_middleware(TrustedHostMiddleware")
