"""What the outgoing-mail templates must and must not escape.

`khoj.routers.email` renders the HTML mails through a Jinja environment with
autoescape on (a fork hardening: names, queries and feedback text come from users and
from model output, and must not become markup). Autoescape is blind to *why* a string
contains markup, so the one value that is HTML on purpose -- an automation result that
has already been through the markdown renderer -- has to be marked safe explicitly.
Otherwise every automation mail shows literal `<p>` tags.

Only Jinja is real here. Django, Resend and the markdown renderer are stubs, so the
test needs nothing but `requirements-dev.txt`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import shutil
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
EMAIL_TEMPLATES = SRC / "khoj" / "interface" / "email"
EMAIL_ROUTER = SRC / "khoj" / "routers" / "email.py"

sys.path.insert(0, str(SRC))


class _FakeMarkdownIt:
    def render(self, text: str) -> str:
        return f"<p>{text}</p>\n"


@pytest.fixture
def mail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Load the real email router with Resend enabled; return the mails it "sent"."""
    # collectstatic copies interface/email into BASE_DIR/static; mirror that.
    shutil.copytree(EMAIL_TEMPLATES, tmp_path / "static")
    sent: list[dict] = []

    resend = types.ModuleType("resend")
    resend.Emails = types.SimpleNamespace(send=lambda payload: sent.append(payload) or payload)
    django = types.ModuleType("django")
    django_conf = types.ModuleType("django.conf")
    django_conf.settings = types.SimpleNamespace(BASE_DIR=str(tmp_path))
    markdown_it = types.ModuleType("markdown_it")
    markdown_it.MarkdownIt = _FakeMarkdownIt
    helpers = types.ModuleType("khoj.utils.helpers")
    helpers.is_none_or_empty = lambda value: value is None or value == ""

    for name, module in {
        "resend": resend,
        "django": django,
        "django.conf": django_conf,
        "markdown_it": markdown_it,
        "khoj.utils.helpers": helpers,
    }.items():
        monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setenv("RESEND_API_KEY", "test-key")

    spec = importlib.util.spec_from_file_location("email_router_under_test", EMAIL_ROUTER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, sent


def test_automation_result_keeps_its_rendered_markup(mail) -> None:
    """An escaped result shows the reader `&lt;p&gt;` instead of a paragraph."""
    router, sent = mail

    router.send_task_email("Ada", "ada@example.com", "daily news", "hello", "Digest")

    html = sent[0]["html"]
    assert "<p>hello</p>" in html
    assert "&lt;p&gt;hello" not in html


def test_untrusted_automation_fields_are_still_escaped(mail) -> None:
    """The reason autoescape is on: subject and query are not markup."""
    router, sent = mail

    router.send_task_email(
        "Ada", "ada@example.com", "<img src=x onerror=alert(1)>", "ok", "<script>alert(1)</script>"
    )

    html = sent[0]["html"]
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert(1)>" not in html


def test_feedback_mail_escapes_user_and_model_text(mail) -> None:
    router, sent = mail

    asyncio.run(
        router.send_query_feedback(
            "<b>query</b>", "<script>reply</script>", "<i>up</i>", "ada@example.com"
        )
    )

    html = sent[0]["html"]
    assert "<script>reply</script>" not in html
    assert "<b>query</b>" not in html
    assert "&lt;b&gt;query&lt;/b&gt;" in html
