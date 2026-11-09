"""Install the product SDK that the offline contract tests run against.

The version is read from khoj's own pins in `pyproject.toml`, never restated here, so a
Dependabot bump of `google-genai` is exercised by the very next gate run. Only the few
packages the contract test needs are installed (not the whole product, which pulls in
torch and whisper).

    python tools/install_contract_deps.py            # pip install the pinned set
    python tools/install_contract_deps.py --print    # only list the requirement lines
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"

# Product dependencies the contract test imports (directly or through the SDK).
CONTRACT_PACKAGES = ("google-genai", "google-auth", "httpx", "pillow")

_DEPENDENCY_LINE = re.compile(r'^\s*"(?P<spec>(?P<name>[A-Za-z0-9_.-]+)[^"]*)",?\s*(#.*)?$')


def _normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def contract_requirements(pyproject_text: str) -> list[str]:
    """Return the pyproject requirement strings for CONTRACT_PACKAGES, in that order.

    Raises LookupError when a package is no longer declared, so the gate fails loudly
    instead of silently testing against whatever happens to be installed.
    """
    in_dependencies = False
    found: dict[str, str] = {}
    for line in pyproject_text.splitlines():
        if re.match(r"^dependencies\s*=\s*\[", line):
            in_dependencies = True
            continue
        if in_dependencies and line.strip().startswith("]"):
            break
        if not in_dependencies:
            continue
        match = _DEPENDENCY_LINE.match(line)
        if match:
            found[_normalise(match["name"])] = match["spec"].strip()
    missing = [name for name in CONTRACT_PACKAGES if name not in found]
    if missing:
        raise LookupError(f"pyproject.toml no longer declares: {', '.join(missing)}")
    return [found[name] for name in CONTRACT_PACKAGES]


def refusal(prefix: str, base_prefix: str, env) -> str | None:
    """Why installing here is refused, or None when it is allowed.

    A gate must not mutate a global interpreter: outside a virtual environment this only
    proceeds on CI, where the runner is disposable.
    """
    if prefix != base_prefix:
        return None
    if env.get("CI", "").lower() == "true" or env.get("GITHUB_ACTIONS", "").lower() == "true":
        return None
    return (
        "Refusing to pip install into the global Python (not inside a virtual environment).\n"
        "Create the maintenance venv first: pwsh -NoProfile -File tools/bootstrap_dev.ps1"
    )


def main(argv: list[str]) -> int:
    requirements = contract_requirements(PYPROJECT.read_text(encoding="utf-8"))
    if "--print" in argv:
        print("\n".join(requirements))
        return 0
    reason = refusal(sys.prefix, sys.base_prefix, os.environ)
    if reason:
        print(reason, file=sys.stderr)
        return 2
    command = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-q", *requirements]
    print("==> " + " ".join(requirements))
    return subprocess.call(command)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
