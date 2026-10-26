#!/usr/bin/env python3
"""檢查本 fork 維護文件之間的相對連結。

只驗公開入口與 docs；不上游 `documentation/` 站點。外部網址交給人看。

    python tools/check_links.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
HTML_SRC_PATTERN = re.compile(r"""(?is)<img[^>]+src=["']([^"']+)["']""")
# READMEs switch language with `<a href="README.en.md">`; Markdown syntax is not the only
# way to write a link, and an unchecked syntax is a link that can rot unnoticed.
HTML_HREF_PATTERN = re.compile(r"""(?is)<a\s[^>]*?href=["']([^"']+)["']""")
# Documentation that explains link syntax shows it in code, and code is not a link.
# An unclosed fence runs to the end of the document, as in CommonMark.
FENCED_CODE = re.compile(
    r"^ {0,3}(`{3,}|~{3,})[^\n]*\n.*?(?:^ {0,3}\1[`~]*[ \t]*$|\Z)", re.DOTALL | re.MULTILINE
)
INLINE_CODE = re.compile(r"(`+)(?!`)[^\n]+?(?<!`)\1(?!`)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "#")
SKIP_NAMES = {
    "upstream-review-report.md",
    "dependency-freshness-report.md",
}
MAINTAINED_DOCUMENTS = (
    "README.md",
    "README.en.md",
    "FORK.md",
    "NOTICE.md",
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "REVIEW.md",
    "docs/DEVELOPMENT.md",
    "docs/DECISIONS.md",
    "docs/UPSTREAM.md",
    ".github/pull_request_template.md",
)


def iter_documents() -> list[Path]:
    missing = [relative for relative in MAINTAINED_DOCUMENTS if not (ROOT / relative).is_file()]
    if missing:
        raise FileNotFoundError("maintained documents missing: " + ", ".join(missing))
    extra = []
    # Any Markdown under docs/ is maintained documentation: a new file there must not
    # need a second edit to this list before its links are checked.
    for folder, pattern in ((ROOT / ".github", "**/*.md"), (ROOT / "docs", "*.md")):
        if folder.is_dir():
            extra.extend(
                path
                for path in sorted(folder.glob(pattern))
                if path.is_file() and path.name not in SKIP_NAMES
            )
    required = [ROOT / relative for relative in MAINTAINED_DOCUMENTS]
    seen = {path.resolve() for path in required}
    for path in extra:
        if path.resolve() not in seen:
            required.append(path)
            seen.add(path.resolve())
    return required


def _destination(raw: str) -> str:
    """The path part of `(...)` in `[text](...)`, without the optional title.

    `[t](path "title")` points at `path`. Only an angle-bracketed destination may
    contain spaces, so a bare destination ends at the first whitespace.
    """
    raw = raw.strip()
    if raw.startswith("<"):
        end = raw.find(">")
        return raw[1:end] if end != -1 else raw[1:]
    return raw.split(None, 1)[0] if raw else ""


def _missing_relative(path: Path, target: str) -> str | None:
    target = _destination(target)
    if not target or target.startswith(SKIP_PREFIXES):
        return None
    file_part = unquote(target.split("#", 1)[0])
    if not file_part:
        return None
    resolved = (path.parent / file_part).resolve()
    if resolved.exists():
        return None
    try:
        shown = resolved.relative_to(ROOT)
    except ValueError:
        shown = resolved
    return f"{target} → 找不到 {shown}"


def check_document(path: Path) -> list[str]:
    problems: list[str] = []
    text = INLINE_CODE.sub("", FENCED_CODE.sub("", path.read_text(encoding="utf-8")))
    for pattern in (LINK_PATTERN, IMAGE_PATTERN, HTML_SRC_PATTERN, HTML_HREF_PATTERN):
        for match in pattern.finditer(text):
            missing = _missing_relative(path, match.group(1))
            # `![a](x)` also matches the plain-link pattern; report a link once.
            if missing and missing not in problems:
                problems.append(missing)
    return problems


def tolerate_unencodable_output() -> None:
    """Never let the console's code page decide whether a finished check succeeds.

    Piped on Windows, stdout uses the ANSI code page, but the summary line (and any
    file name or link text it echoes) is Chinese. Unencodable characters become `?` on
    the console instead of raising UnicodeEncodeError mid-report.
    """
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")


def main() -> int:
    tolerate_unencodable_output()
    documents = iter_documents()
    if not documents:
        print("找不到任何維護用 Markdown 檔")
        return 1

    failures = 0
    for path in documents:
        problems = check_document(path)
        rel = path.relative_to(ROOT)
        if problems:
            failures += 1
            for problem in problems:
                print(f"FAIL {rel}: {problem}")
        else:
            print(f"OK   {rel}")

    print(f"\n共 {len(documents)} 份文件，{failures} 份有斷掉的相對連結。")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
