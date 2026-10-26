"""The telemetry server ships as its own image, not as part of the Khoj package.

`src/telemetry/Dockerfile` installs `requirements.txt` and copies `telemetry.py`
alone to `/app/main.py` (build context `src/telemetry`). Anything the module imports
that is neither standard library nor declared in that requirements file does not
exist inside the container, and the server dies with ModuleNotFoundError at start.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TELEMETRY_DIR = ROOT / "src" / "telemetry"

# requirements.txt names the distribution; the import name can differ.
IMPORT_NAME_OF_DISTRIBUTION = {"python-dotenv": "dotenv"}


def imported_top_level_modules(source: str) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def declared_modules(requirements: str) -> set[str]:
    declared: set[str] = set()
    for line in requirements.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        name = re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0].lower()
        declared.add(IMPORT_NAME_OF_DISTRIBUTION.get(name, name.replace("-", "_")))
    return declared


def test_telemetry_server_only_imports_what_its_image_provides() -> None:
    imported = imported_top_level_modules(
        (TELEMETRY_DIR / "telemetry.py").read_text(encoding="utf-8")
    )
    available = set(sys.stdlib_module_names) | declared_modules(
        (TELEMETRY_DIR / "requirements.txt").read_text(encoding="utf-8")
    )
    assert sorted(imported - available) == []


def test_telemetry_log_sanitizer_matches_the_shared_one() -> None:
    """The server carries its own copy, so a drift would go unnoticed without this."""
    sys.path.insert(0, str(ROOT / "src"))
    from khoj.utils.security import sanitize_log_value as shared

    tree = ast.parse((TELEMETRY_DIR / "telemetry.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "sanitize_log_value"
    )
    namespace: dict[str, object] = {}
    exec(compile(ast.Module([function], type_ignores=[]), "telemetry.py", "exec"), namespace)
    local = namespace["sanitize_log_value"]

    for value in ("plain", "a\r\nforged", "x\ny", ["a\nb"], 7, None):
        assert local(value) == shared(value)  # type: ignore[operator]
    assert local("safe\r\nforged") == r"safe\r\nforged"  # type: ignore[operator]


def test_requirement_parsing_handles_extras_and_pins() -> None:
    assert declared_modules("uvicorn[standard]>=0.30  # server\npython-dotenv==1.0\n") == {
        "uvicorn",
        "dotenv",
    }
