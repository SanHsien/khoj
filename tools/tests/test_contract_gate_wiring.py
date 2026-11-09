"""The google-genai contract test only protects if the gate runs it with the SDK present.

`test_google_genai_contract.py` skips when the SDK is missing and the opt-in variable is
unset. Everything that runs `tools/tests` as a gate must therefore install the pinned SDK
and set the variable, otherwise the test turns into decoration that reports green.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from install_contract_deps import CONTRACT_PACKAGES, contract_requirements  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REQUIRE = "KHOJ_REQUIRE_GENAI_CONTRACT"
INSTALL = "install_contract_deps.py"
PYPROJECT_TEXT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_requirements_come_from_the_product_pins() -> None:
    requirements = contract_requirements(PYPROJECT_TEXT)
    assert len(requirements) == len(CONTRACT_PACKAGES)
    sdk = next(r for r in requirements if r.startswith("google-genai"))
    assert re.fullmatch(r"google-genai\s*==\s*\d+(\.\d+)*", sdk), sdk
    assert sdk in PYPROJECT_TEXT


def test_a_dropped_product_pin_fails_instead_of_testing_whatever_is_installed() -> None:
    without_sdk = PYPROJECT_TEXT.replace('"google-genai', '"not-genai')
    with pytest.raises(LookupError, match="google-genai"):
        contract_requirements(without_sdk)


def test_requirements_ignore_optional_dependency_groups() -> None:
    text = 'dependencies = [\n    "httpx == 1",\n]\n[project.optional-dependencies]\ndev = [\n    "pillow == 2",\n]\n'
    with pytest.raises(LookupError, match="pillow"):
        contract_requirements(text)


def test_dev_check_installs_the_sdk_before_pytest_and_requires_the_contract() -> None:
    script = (ROOT / "tools" / "dev_check.ps1").read_text(encoding="utf-8")
    assert f'$env:{REQUIRE} = "1"' in script
    assert script.index(INSTALL) < script.index("-m\", \"pytest")


def test_every_ci_job_that_runs_the_tools_tests_installs_the_sdk_and_requires_it() -> None:
    text = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    jobs = re.split(r"\n  (?=[\w-]+:\n)", text.split("\njobs:\n", 1)[1])
    runs_pytest = "-m pytest -c tools/pytest.ini"
    gating = [job for job in jobs if runs_pytest in job or "dev_check.ps1" in job]
    assert gating, "no CI job runs the tools tests"
    for job in gating:
        name = job.splitlines()[0]
        assert REQUIRE in job, f"{name} does not require the contract test"
        if runs_pytest in job:
            assert INSTALL in job, f"{name} does not install the pinned SDK"
            assert job.index(INSTALL) < job.index(runs_pytest), name
