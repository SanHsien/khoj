from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_links  # noqa: E402
import check_upstream_updates as checker  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PUBLISH_WORKFLOWS = (
    "pypi.yml",
    "dockerize.yml",
    "github_pages_deploy.yml",
    "release.yml",
    "desktop.yml",
    "dockerize_telemetry_server.yml",
    "run_evals.yml",
)
PRODUCT_CI_WORKFLOWS = (
    "test.yml",
    "pre-commit.yml",
    "build_khoj_el.yml",
    "test_khoj_el.yml",
)


def test_maintainer_markdown_links_resolve() -> None:
    failures = 0
    for path in check_links.iter_documents():
        problems = check_links.check_document(path)
        failures += len(problems)
        for problem in problems:
            print(f"{path}: {problem}")
    assert failures == 0


def test_required_overlay_files_exist() -> None:
    required = (
        "README.md",
        "README.en.md",
        "FORK.md",
        "NOTICE.md",
        "AGENTS.md",
        "CLAUDE.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "REVIEW.md",
        "docs/DEVELOPMENT.md",
        "docs/DECISIONS.md",
        "docs/UPSTREAM.md",
        "tools/dev_check.ps1",
        "tools/bootstrap_dev.ps1",
        "LICENSE",
    )
    missing = [name for name in required if not (ROOT / name).is_file()]
    assert missing == []


def test_readme_pair_cross_links_and_names_the_fork() -> None:
    zh = (ROOT / "README.md").read_text(encoding="utf-8")
    en = (ROOT / "README.en.md").read_text(encoding="utf-8")
    assert "README.en.md" in zh
    assert "README.md" in en
    assert "khoj-ai/khoj" in zh
    assert "khoj-ai/khoj" in en
    assert "FORK.md" in zh
    assert "AGPL" in zh
    assert "tools\\bootstrap_dev.ps1" in zh or "tools/bootstrap_dev.ps1" in zh


def test_gitignore_covers_user_data_and_reports() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert ".venv" in text
    assert "src/interface/android/local.properties" in text
    assert "notes/" in text
    assert "vaults/" in text
    assert "conversations.json" in text
    assert ".khoj/" in text
    assert "upstream-review-report.md" in text
    assert "dependency-freshness-report.md" in text


def test_review_snapshot_has_required_sections() -> None:
    text = (ROOT / "REVIEW.md").read_text(encoding="utf-8")
    assert "## 結論" in text
    assert "## 已修 findings" in text
    assert "## 接受、不改契約" in text
    assert "## 尚未宣稱範圍" in text
    assert "docker-compose.yml" in text
    assert "KHOJ_TELEMETRY_DISABLE" in text or "遙測" in text


def test_security_docs_cover_compose_defaults() -> None:
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "anonymous-mode" in security
    assert "KHOJ_TELEMETRY_DISABLE" in security
    assert "KHOJ_DJANGO_SECRET_KEY" in security
    assert "KHOJ_DJANGO_SECRET_KEY" in readme
    assert "KHOJ_TELEMETRY_DISABLE" in readme
    assert "127.0.0.1" in readme
    assert "--profile operator" in readme


def test_compose_overlay_hardens_local_defaults() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "127.0.0.1:42110:42110" in compose
    assert "127.0.0.1:5900:5900" in compose
    assert '"5900:5900"' not in compose
    assert "KHOJ_TELEMETRY_DISABLE=True" in compose
    command_lines = [line for line in compose.splitlines() if line.lstrip().startswith("command:")]
    assert command_lines, "server command missing"
    assert all("--anonymous-mode" not in line for line in command_lines)
    assert "profiles:" in compose
    assert "operator" in compose


def test_operator_overlay_avoids_eval_and_shell_flag() -> None:
    uitars = (ROOT / "src/khoj/processor/operator/grounding_agent_uitars.py").read_text(
        encoding="utf-8"
    )
    computer = (
        ROOT / "src/khoj/processor/operator/operator_environment_computer.py"
    ).read_text(encoding="utf-8")
    assert uitars.count("eval(") == uitars.count("literal_eval(")
    assert "shell=True" not in computer
    assert '["bash", "-c", command]' in computer


def test_ci_covers_python_314() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert '"3.14"' in workflow
    assert "windows / py3.14" in workflow
    assert "tools/dev_check.ps1" in workflow or "tools\\dev_check.ps1" in workflow
    assert "-c tools/pytest.ini" in workflow


def test_publish_workflows_are_gated_to_upstream() -> None:
    for name in PUBLISH_WORKFLOWS:
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "github.repository == 'khoj-ai/khoj'" in text, name


def test_product_ci_workflows_are_gated_to_upstream() -> None:
    for name in PRODUCT_CI_WORKFLOWS:
        text = (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")
        assert "github.repository == 'khoj-ai/khoj'" in text, name


def test_baseline_file_is_valid_and_complete() -> None:
    baseline = checker.load_baseline()
    assert baseline["repo"] == "https://github.com/khoj-ai/khoj.git"
    assert baseline["branch"] == "master"
    assert len(baseline["reviewed_through"]) == 40
    assert baseline["reviewed_through"] == "ae229ca894c0b80ad84664afcfdde523b5e87057"
    assert baseline["reviewed_date"] == "2026-08-27"


def test_workflow_is_scheduled_and_fails_on_unreviewed_commits() -> None:
    workflow = (ROOT / ".github" / "workflows" / "upstream-check.yml").read_text(
        encoding="utf-8"
    )
    assert "schedule:" in workflow
    assert "cron:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "tools/check_upstream_updates.py" in workflow
    assert "fetch-depth: 0" in workflow
    assert "exit 1" in workflow


def test_render_markdown_reports_no_new_commits() -> None:
    baseline = {
        "repo": "https://example.invalid/upstream.git",
        "branch": "master",
        "reviewed_through": "a" * 40,
        "reviewed_date": "2026-08-27",
    }
    report = checker.render_markdown(baseline, [])
    assert "No new upstream commits" in report


def test_load_baseline_rejects_missing_file(tmp_path: Path) -> None:
    try:
        checker.load_baseline(tmp_path / "nope.json")
    except checker.UpstreamCheckError:
        return
    raise AssertionError("expected UpstreamCheckError")


def test_baseline_matches_decisions_record() -> None:
    decisions = (ROOT / "docs" / "DECISIONS.md").read_text(encoding="utf-8")
    upstream = (ROOT / "docs" / "UPSTREAM.md").read_text(encoding="utf-8")
    baseline = json.loads((ROOT / "tools" / "upstream_baseline.json").read_text(encoding="utf-8"))
    assert baseline["reviewed_date"] in decisions
    assert "ae229ca" in upstream
    assert "khoj-ai/khoj" in decisions
