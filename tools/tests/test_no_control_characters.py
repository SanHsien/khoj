"""Maintained text files must not carry stray control characters.

A backslash-b written through a non-raw string once turned `tools\bootstrap_dev.ps1` in
docs/DEVELOPMENT.md into a literal backspace byte (0x08), invisible in review and broken
when copied. Tab, newline and carriage return are the only C0 controls allowed.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTROL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
SUFFIXES = {".md", ".ps1", ".py"}
SCANNED_DIRS = {"docs", "tools"}


def offending_lines(text: str) -> list[int]:
    return [number for number, line in enumerate(text.split("\n"), 1) if CONTROL.search(line)]


def candidate_files() -> list[str]:
    def listing(*args: str) -> list[str]:
        out = subprocess.check_output(["git", "ls-files", "-z", *args], cwd=ROOT, text=True)
        return [name for name in out.split("\0") if name]

    # Untracked files count too: the mistake should be caught before it is committed.
    names = listing() + listing("--others", "--exclude-standard")
    return [
        name
        for name in names
        if Path(name).suffix in SUFFIXES and (len(Path(name).parts) == 1 or Path(name).parts[0] in SCANNED_DIRS)
    ]


def test_detector_flags_backspace_but_not_tab_newline_or_carriage_return() -> None:
    assert offending_lines("ok\ttab\r\nline two\n") == []
    assert offending_lines("run tools\x08ootstrap_dev.ps1\n") == [1]
    assert offending_lines("fine\nbell\x07\nescape\x1b[0m\n") == [2, 3]


def test_no_maintained_file_contains_a_stray_control_character() -> None:
    offenders = []
    for name in candidate_files():
        path = ROOT / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        offenders += [f"{name}:{number}" for number in offending_lines(text)]
    assert offenders == []
