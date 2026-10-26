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


def test_summary_survives_a_console_that_cannot_encode_chinese(
    monkeypatch, tmp_path: Path
) -> None:
    """Piped on Windows the console is the ANSI code page, and the summary is Chinese."""
    (tmp_path / "README.md").write_text("no links here\n", encoding="utf-8")
    monkeypatch.setattr(check_links, "ROOT", tmp_path)
    monkeypatch.setattr(check_links, "MAINTAINED_DOCUMENTS", ("README.md",))
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


def test_a_link_title_is_not_part_of_the_path(doc) -> None:
    """`[text](path "title")` is valid Markdown and points at `path`."""
    assert doc('[ok](exists.md "A title")') == []
    problems = doc('[bad](missing.md "A title")')
    assert len(problems) == 1
    assert "missing.md" in problems[0]


def test_angle_bracket_destination_with_spaces_and_a_title(doc, tmp_path: Path) -> None:
    (tmp_path / "my file.md").write_text("x\n", encoding="utf-8")
    assert doc('[ok](<my file.md> "t")') == []


def test_a_broken_image_is_reported_once(doc) -> None:
    assert len(doc("![alt](missing.png)")) == 1


def test_every_markdown_file_under_docs_is_checked(monkeypatch, tmp_path: Path) -> None:
    """A document added to docs/ must not need a second edit to be link-checked."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "README.md").write_text("hi\n", encoding="utf-8")
    (tmp_path / "docs" / "NEW.md").write_text("[x](gone.md)\n", encoding="utf-8")
    monkeypatch.setattr(check_links, "ROOT", tmp_path)
    monkeypatch.setattr(check_links, "MAINTAINED_DOCUMENTS", ("README.md",))

    documents = check_links.iter_documents()

    assert tmp_path / "docs" / "NEW.md" in documents


def test_link_syntax_inside_code_is_an_example_not_a_link(doc) -> None:
    """Docs describe link syntax in backticks and fences; that text is not a link."""
    body = (
        "Write `[text](gone.md)` or `<a href=\"gone.md\">` to link.\n"
        "\n"
        "```markdown\n"
        "[text](gone.md)\n"
        "```\n"
        "\n"
        "~~~\n"
        "![alt](gone.png)\n"
        "~~~\n"
    )
    assert doc(body) == []


def test_a_real_link_next_to_code_is_still_checked(doc) -> None:
    body = "Use `[a](gone.md)` but see [this](missing.md) and [that](exists.md).\n"
    problems = doc(body)
    assert len(problems) == 1
    assert "missing.md" in problems[0]


def test_link_text_that_is_code_still_counts_as_a_link(doc) -> None:
    assert doc("[`exists.md`](exists.md)\n") == []
    assert len(doc("[`gone.md`](gone.md)\n")) == 1


def test_an_unclosed_fence_hides_the_rest_of_the_document_like_markdown_does(doc) -> None:
    assert doc("```\n[x](gone.md)\n") == []
