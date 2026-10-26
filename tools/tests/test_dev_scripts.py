"""The PowerShell entry points must not report success for a step that failed.

PowerShell does not stop on a non-zero native exit code, even with
`$ErrorActionPreference = "Stop"`. A script that runs a native command and carries on
prints its success banner and exits 0 after the gate went red -- the green line then
vouches for an environment nobody verified.
"""

from __future__ import annotations

import re
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]

NATIVE_CALL = re.compile(r"^(?:&\s+|python\s)")
EXIT_CODE_GUARD = re.compile(r"^if\s*\(\$LASTEXITCODE\b")


def unguarded_native_calls(script: str) -> list[str]:
    lines = [line.strip() for line in script.splitlines() if line.strip()]
    missing = []
    for index, line in enumerate(lines):
        if not NATIVE_CALL.match(line):
            continue
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if not EXIT_CODE_GUARD.match(following):
            missing.append(line)
    return missing


def test_bootstrap_checks_the_exit_code_of_every_native_step() -> None:
    script = (TOOLS / "bootstrap_dev.ps1").read_text(encoding="utf-8")
    assert unguarded_native_calls(script) == []


def test_bootstrap_does_not_announce_success_before_the_gate_has_passed() -> None:
    script = (TOOLS / "bootstrap_dev.ps1").read_text(encoding="utf-8")
    gate = script.index("dev_check.ps1")
    banner = script.index("維護環境可用")
    guard = script.find("$LASTEXITCODE", gate)
    assert guard != -1, "nothing checks the exit code of the gate"
    assert gate < guard < banner


def test_detector_flags_a_native_call_that_nobody_checks() -> None:
    script = "Write-Host hi\n& pwsh -File gate.ps1\nWrite-Host done\n"
    assert unguarded_native_calls(script) == ["& pwsh -File gate.ps1"]
    guarded = "& pwsh -File gate.ps1\nif ($LASTEXITCODE -ne 0) { throw 'x' }\n"
    assert unguarded_native_calls(guarded) == []
