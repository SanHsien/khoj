"""What the relative-link checker has to notice, and what it must not invent.

Every case is a link a reader can click in the rendered Markdown on GitHub.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_links  # noqa: E402


def test_summary_survives_a_console_that_cannot_encode_chinese(monkeypatch) -> None:
    """Piped on Windows the console is the ANSI code page, and the summary is Chinese."""
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    assert check_links.main() == 0
