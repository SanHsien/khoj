"""What the outgoing-mail templates must and must not escape.

`khoj.routers.email` renders the HTML mails through a Jinja environment with
autoescape on (a fork hardening: names, queries and feedback text come from users and
from model output, and must not become markup). Autoescape is blind to *why* a string
contains markup, so the one value that is HTML on purpose -- an automation result that
has already been through the markdown renderer -- has to be marked safe explicitly.
Otherwise every automation mail shows literal `<p>` tags.

Jinja and the markdown renderer are real. Django and Resend are stubs, so the test needs
nothing but `requirements-dev.txt`.
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
    helpers = types.ModuleType("khoj.utils.helpers")
    helpers.is_none_or_empty = lambda value: value is None or value == ""

    for name, module in {
        "resend": resend,
        "django": django,
        "django.conf": django_conf,
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


UNTRUSTED_RESULT = (
    "Hello <img src=https://x/t.png> <script>alert(1)</script> "
    "<a href=javascript:alert(1)>click</a> "
    "<a href=\"https://evil.example\">phish</a>"
)


def test_raw_html_in_an_automation_result_does_not_reach_the_mail_as_markup(mail) -> None:
    """The result comes from a model reading web pages; it is not trusted markup.

    `result` is marked safe so that the rendered markdown survives, which means whatever
    the renderer lets through goes into the mail verbatim. The renderer must therefore
    not pass raw HTML.
    """
    router, sent = mail

    router.send_task_email("Ada", "ada@example.com", "q", UNTRUSTED_RESULT, "Digest")

    html = sent[0]["html"]
    assert "<script>" not in html
    assert "<img src=https://x/t.png>" not in html
    assert "<a href=javascript:alert(1)>" not in html
    assert '<a href="https://evil.example">' not in html
    # Escaped, not dropped: the reader can still see what the model wrote.
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_markdown_syntax_in_an_automation_result_still_renders(mail) -> None:
    router, sent = mail

    router.send_task_email(
        "Ada",
        "ada@example.com",
        "q",
        "**bold** and a [link](https://example.com/a)\n\n- one\n- two\n",
        "Digest",
    )

    html = sent[0]["html"]
    assert "<strong>bold</strong>" in html
    assert '<a href="https://example.com/a">link</a>' in html
    assert "<li>one</li>" in html


def test_markdown_link_with_a_javascript_url_is_not_rendered_as_a_link(mail) -> None:
    router, sent = mail

    router.send_task_email("Ada", "ada@example.com", "q", "[x](javascript:alert(1))", "Digest")

    assert 'href="javascript:' not in sent[0]["html"]
