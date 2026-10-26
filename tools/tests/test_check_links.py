"""What the relative-link checker has to notice, and what it must not invent.

Every case is a link a reader can click in the rendered Markdown on GitHub.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_links  # noqa: E402


@pytest.fixture
def doc(tmp_path: Path):
    """Write `body` next to an existing sibling file and return the check function."""
    (tmp_path / "exists.md").write_text("# there\n", encoding="utf-8")

    def check(body: str) -> list[str]:
        path = tmp_path / "doc.md"
        path.write_text(body, encoding="utf-8")
        return check_links.check_document(path)

    return check


def test_summary_survives_a_console_that_cannot_encode_chinese(monkeypatch) -> None:
    """Piped on Windows the console is the ANSI code page, and the summary is Chinese."""
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    assert check_links.main() == 0


def test_html_anchor_href_to_a_missing_file_is_reported(doc) -> None:
    """The README language switcher is an `<a href>`; a broken one went unnoticed."""
    problems = doc('<a href="missing.md">x</a> <a href="exists.md">ok</a>')
    assert len(problems) == 1
    assert "missing.md" in problems[0]


def test_external_and_fragment_hrefs_are_not_treated_as_files(doc) -> None:
    body = '<a href="https://example.com/x">a</a> <a href="#top">b</a> <a href="mailto:a@b.c">c</a>'
    assert doc(body) == []
