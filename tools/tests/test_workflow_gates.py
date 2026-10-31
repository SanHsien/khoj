"""Every job of an inherited workflow must be gated to the upstream repository.

`test_fork_docs.py` checks that the gate string appears somewhere in each publish
workflow. That is not the property: a second job added to `pypi.yml` (or a new upstream
workflow arriving through a sync) without its own `if:` would still pass while it
publishes from this fork. The unit of protection is the job.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# Written by this fork, meant to run here. Everything else came from upstream.
FORK_OWN = {
    "ci.yml",
    "codeql.yml",
    "dependency-freshness.yml",
    "docker-build-check.yml",
    "docker-compose-smoke.yml",
    "upstream-check.yml",
}
GATE = re.compile(r"^if:\s*.*github\.repository == 'khoj-ai/khoj'")


def jobs_and_their_keys(text: str) -> dict[str, list[tuple[int, str]]]:
    """Map job name -> (indent, stripped line) for the lines inside that job."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(r"^jobs:\s*$", line))
    jobs: dict[str, list[tuple[int, str]]] = {}
    job_indent: int | None = None
    current: str | None = None
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        if job_indent is None:
            job_indent = indent
        if indent == job_indent and re.fullmatch(r"[\w-]+:", stripped):
            current = stripped[:-1]
            jobs[current] = []
        elif current is not None:
            jobs[current].append((indent, stripped))
    return jobs


def ungated_jobs(text: str) -> list[str]:
    missing = []
    for name, body in jobs_and_their_keys(text).items():
        direct_child_indent = min((indent for indent, _ in body), default=0)
        if not any(
            indent == direct_child_indent and GATE.match(line) for indent, line in body
        ):
            missing.append(name)
    return missing


def test_detector_finds_the_job_that_lacks_its_own_gate() -> None:
    workflow = (
        "name: x\n"
        "jobs:\n"
        "  build:\n"
        "    if: github.repository == 'khoj-ai/khoj'\n"
        "    runs-on: ubuntu-latest\n"
        "  publish:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - if: github.repository == 'khoj-ai/khoj'\n"
        "        run: echo a step-level gate does not protect the job\n"
    )
    assert ungated_jobs(workflow) == ["publish"]


def test_detector_follows_the_indentation_the_workflow_uses() -> None:
    workflow = (
        "jobs:\n"
        "    deploy:\n"
        "      if: github.repository == 'khoj-ai/khoj'\n"
        "      runs-on: ubuntu-latest\n"
    )
    assert ungated_jobs(workflow) == []


def test_every_job_of_every_inherited_workflow_is_gated_to_upstream() -> None:
    inherited = sorted(
        path for path in WORKFLOWS.glob("*.yml") if path.name not in FORK_OWN
    )
    assert inherited, "no inherited workflows found; is the path right?"
    ungated = {
        path.name: ungated_jobs(path.read_text(encoding="utf-8"))
        for path in inherited
        if ungated_jobs(path.read_text(encoding="utf-8"))
    }
    assert ungated == {}
