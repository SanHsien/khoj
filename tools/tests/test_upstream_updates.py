"""What the upstream checker must not be allowed to do.

Every test here names a way the check could go quiet without anybody deciding
to stop watching upstream.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import check_upstream_updates as checker  # noqa: E402, I001


BASELINE = {
    "repo": "https://github.com/example/product.git",
    "branch": "main",
    "reviewed_through": "a" * 40,
    "reviewed_date": "2026-08-29",
}


def fake_gh(payload: object, returncode: int = 0):
    """Stand in for `gh`, so no test reaches the network."""

    def runner(args, **kwargs):
        assert args[0] == "gh"
        assert "--state" in args and args[args.index("--state") + 1] == "all"
        return subprocess.CompletedProcess(
            args, returncode, stdout=json.dumps(payload), stderr=""
        )

    return runner


def test_tickets_are_queried_with_state_all(monkeypatch):
    """An item opened and closed between two runs was still never triaged."""
    monkeypatch.setattr(
        checker.subprocess,
        "run",
        fake_gh([{"number": 9, "title": "closed without merging"}]),
    )
    tickets = checker.collect_new_tickets(BASELINE, "pr")
    assert tickets == [{"number": 9, "title": "closed without merging"}]


def test_items_at_or_below_the_watermark_are_not_re_reported(monkeypatch):
    monkeypatch.setattr(
        checker.subprocess,
        "run",
        fake_gh([{"number": 4, "title": "old"}, {"number": 5, "title": "new"}]),
    )
    baseline = {**BASELINE, "reviewed_pr_through": 4}
    assert [t["number"] for t in checker.collect_new_tickets(baseline, "pr")] == [5]


def test_ticket_titles_survive_undecodable_bytes(monkeypatch):
    """Titles are written by strangers and the console is not always UTF-8.

    Without an explicit `errors`, one undecodable byte kills the whole upstream
    check instead of costing one garbled character.
    """
    captured = {}

    def runner(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr(checker.subprocess, "run", runner)
    checker.collect_new_tickets(BASELINE, "pr")

    assert captured["errors"] == "replace"


def test_gh_failure_reports_unchecked_rather_than_empty(monkeypatch):
    """`None`, not `[]`: "not checked" must never render as "nothing to review"."""
    monkeypatch.setattr(checker.subprocess, "run", fake_gh([], returncode=1))
    assert checker.collect_new_tickets(BASELINE, "issue") is None


def test_missing_gh_executable_reports_unchecked_rather_than_crashing(monkeypatch):
    """A machine without `gh` must get "Not checked", not a traceback.

    `subprocess.run` raises FileNotFoundError when the executable is absent, which is
    not a non-zero exit code; without a handler the report file is never written and
    the process dies with exit 1 -- the code `--strict` uses for "work to review".
    """

    def runner(args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "gh")

    monkeypatch.setattr(checker.subprocess, "run", runner)
    assert checker.collect_new_tickets(BASELINE, "pr") is None


def test_missing_git_executable_is_a_check_error_not_a_traceback(monkeypatch, tmp_path):
    def runner(args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", "git")

    monkeypatch.setattr(checker.subprocess, "run", runner)
    with pytest.raises(checker.UpstreamCheckError, match="could not run"):
        checker.run_git(["status"], tmp_path)


def _run_main(monkeypatch, tmp_path, *, commits, prs, issues, argv=()):
    output = tmp_path / "report.md"
    monkeypatch.setattr(sys, "argv", ["check_upstream_updates.py", "--output", str(output), *argv])
    monkeypatch.setattr(checker, "load_baseline", lambda: BASELINE)
    monkeypatch.setattr(checker, "fetch_upstream", lambda baseline, repo_dir: "refs/x")
    monkeypatch.setattr(checker, "collect_new_commits", lambda baseline, repo_dir, ref: commits)
    monkeypatch.setattr(
        checker, "collect_new_tickets", lambda baseline, kind: prs if kind == "pr" else issues
    )
    return checker.main(), output.read_text(encoding="utf-8")


def test_unenumerable_tickets_fail_closed_with_exit_code_two(monkeypatch, tmp_path):
    """The exit code is the only thing a scheduler reads; "unknown" must not be 0."""
    code, report = _run_main(monkeypatch, tmp_path, commits=[], prs=None, issues=[])
    assert code == 2
    assert "Not checked" in report


def test_strict_exit_code_distinguishes_work_to_review_from_a_broken_check(
    monkeypatch, tmp_path
):
    ticket = [{"number": 9, "title": "t"}]
    code, _ = _run_main(
        monkeypatch, tmp_path, commits=[], prs=ticket, issues=[], argv=("--strict",)
    )
    assert code == 1
    code, _ = _run_main(monkeypatch, tmp_path, commits=[], prs=[], issues=[], argv=("--strict",))
    assert code == 0


def test_report_says_so_when_tickets_could_not_be_enumerated():
    report = checker.render_markdown(BASELINE, [], prs=None, issues=None)
    assert "Not checked" in report


def test_report_covers_all_three_axes_even_when_commits_are_clean():
    report = checker.render_markdown(BASELINE, [], prs=[], issues=[])
    assert "## Commits" in report
    assert "## Upstream pull requests" in report
    assert "## Upstream issues" in report


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://github.com/example/product.git", "example/product"),
        ("https://github.com/example/product", "example/product"),
        ("git@github.com:example/product.git", "example/product"),
        ("https://gitlab.com/example/product.git", None),
    ],
)
def test_upstream_slug(url, expected):
    assert checker.upstream_slug(url) == expected


def test_shipped_baseline_matches_the_documented_upstream():
    baseline = checker.load_baseline()
    assert checker.upstream_slug(baseline["repo"]) is not None
