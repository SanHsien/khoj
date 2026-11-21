"""Chat cost accounting: cache reads, thinking tokens and cached prompt tokens.

Why this exists: upstream PR #1470 showed the reported chat cost was wrong in ways that
need no new dependency to fix: Gemini cache prices sat under a key the cost function
never reads, Gemini thinking tokens cost nothing, prompt token counts that already
include cached tokens were billed again as cache reads, and some list prices were stale.
This fork ports those fixes without the `llm-prices` dependency the PR adds
(docs/DECISIONS.md 2026-11-21).

How: AST-load the unchanged product bodies (no Django, torch or provider SDK import) and
call them with plain stand-in usage objects.
"""

import ast
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src/khoj"


def load(relative_path, names, namespace=None):
    """Execute the named top-level functions and assignments of a product module."""
    namespace = {} if namespace is None else namespace
    path = ROOT / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    selected, found = [], set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            selected.append(node)
            found.add(node.name)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in names:
            selected.append(node)
            found.add(node.target.id)
    assert set(names) <= found, (relative_path, set(names) - found)
    namespace.setdefault("Dict", dict)
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.Module(body=future + selected, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


@pytest.fixture(scope="module")
def cost():
    constants = SimpleNamespace(**load("utils/constants.py", ["model_to_cost"]))
    return load("utils/helpers.py", ["get_cost_of_chat_message"], {"constants": constants})["get_cost_of_chat_message"]


def test_gemini_cache_reads_are_priced(cost):
    # https://ai.google.dev/gemini-api/docs/pricing context caching: 2.5 Flash $0.03, 2.5 Pro $0.125 per 1M
    assert cost("gemini-2.5-flash", cache_read_tokens=1_000_000) == pytest.approx(0.03)
    assert cost("gemini-2.5-pro", cache_read_tokens=1_000_000) == pytest.approx(0.125)
    assert cost("gemini-3-pro-preview", cache_read_tokens=1_000_000) == pytest.approx(0.20)


def test_gemini_thinking_tokens_are_billed_at_the_output_price(cost):
    # Gemini bills thinking tokens as output tokens ($10 per 1M for 2.5 Pro)
    assert cost("gemini-2.5-pro", thought_tokens=1_000_000) == pytest.approx(10.0)
    total = cost(
        "gemini-2.5-pro", input_tokens=10_000, output_tokens=1_000, thought_tokens=2_000, cache_read_tokens=100_000
    )
    assert total == pytest.approx((10_000 * 1.25 + 3_000 * 10 + 100_000 * 0.125) / 1e6)


def test_gemini_2_0_flash_lite_input_price_is_not_off_by_ten(cost):
    assert cost("gemini-2.0-flash-lite", input_tokens=1_000_000) == pytest.approx(0.075)


def test_claude_4_5_cache_prices_match_the_provider(cost):
    # Anthropic pricing: Opus 4.5 cache hits $0.50; Haiku 4.5 cache hits $0.10, 5m cache writes $1.25
    assert cost("claude-opus-4-5", cache_read_tokens=1_000_000) == pytest.approx(0.50)
    assert cost("claude-opus-4-5-20251101", cache_read_tokens=1_000_000) == pytest.approx(0.50)
    for model in ("claude-haiku-4-5", "claude-haiku-4-5-20251001"):
        assert cost(model, cache_read_tokens=1_000_000, cache_write_tokens=1_000_000) == pytest.approx(0.10 + 1.25)


def test_unknown_and_local_models_cost_nothing(cost):
    assert cost("llama3.1:8b", input_tokens=1_000_000, output_tokens=1_000_000, thought_tokens=1_000_000) == 0
    assert cost("", input_tokens=1_000_000) == 0


def test_gemini_input_tokens_exclude_cached_prompt_tokens():
    # Gemini's prompt_token_count already includes cached_content_token_count
    counts = load("processor/conversation/google/utils.py", ["get_usage_token_counts"])["get_usage_token_counts"]
    usage = SimpleNamespace(
        prompt_token_count=10_000,
        candidates_token_count=200,
        thoughts_token_count=50,
        cached_content_token_count=8_000,
    )
    assert counts(SimpleNamespace(usage_metadata=usage)) == (2_000, 200, 50, 8_000)
    assert counts(SimpleNamespace(usage_metadata=None)) == (0, 0, 0, 0)


def test_chat_completion_input_tokens_exclude_cached_prompt_tokens():
    # OpenAI-compatible prompt_tokens already include prompt_tokens_details.cached_tokens
    counts = load("processor/conversation/openai/utils.py", ["get_chat_completion_usage_token_counts"])[
        "get_chat_completion_usage_token_counts"
    ]
    usage = SimpleNamespace(
        prompt_tokens=10_000,
        completion_tokens=200,
        prompt_tokens_details=SimpleNamespace(cached_tokens=8_000),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=30),
    )
    assert counts(usage) == (2_000, 230, 8_000)
    # Providers that omit the details, or report cached_tokens as null
    bare = SimpleNamespace(
        prompt_tokens=10, completion_tokens=5, prompt_tokens_details=None, completion_tokens_details=None
    )
    assert counts(bare) == (10, 5, 0)
    null_cache = SimpleNamespace(
        prompt_tokens=10,
        completion_tokens=5,
        prompt_tokens_details=SimpleNamespace(cached_tokens=None),
        completion_tokens_details=SimpleNamespace(reasoning_tokens=None),
    )
    assert counts(null_cache) == (10, 5, 0)
    assert counts(None) == (0, 0, 0)


def test_responses_api_null_token_counts_are_zero():
    # Responses API usage: input_tokens include input_tokens_details.cached_tokens. OpenAI-compatible
    # providers can report the detail counts (or the details object) as null; that must not raise.
    counts = load("processor/conversation/openai/utils.py", ["get_responses_usage_token_counts"])[
        "get_responses_usage_token_counts"
    ]
    usage = SimpleNamespace(
        input_tokens=10_000, output_tokens=200, input_tokens_details=SimpleNamespace(cached_tokens=8_000)
    )
    assert counts(SimpleNamespace(usage=usage)) == (2_000, 200, 8_000)
    null_cache = SimpleNamespace(
        input_tokens=10,
        output_tokens=5,
        input_tokens_details=SimpleNamespace(cached_tokens=None),
        output_tokens_details=SimpleNamespace(reasoning_tokens=None),
    )
    assert counts(SimpleNamespace(usage=null_cache)) == (10, 5, 0)
    no_details = SimpleNamespace(input_tokens=10, output_tokens=5, input_tokens_details=None)
    assert counts(SimpleNamespace(usage=no_details)) == (10, 5, 0)
    null_counts = SimpleNamespace(input_tokens=None, output_tokens=None, input_tokens_details=None)
    assert counts(SimpleNamespace(usage=null_counts)) == (0, 0, 0)
    assert counts(SimpleNamespace(usage=None)) == (0, 0, 0)
    assert counts(None) == (0, 0, 0)


def test_responses_api_paths_share_the_null_safe_token_counter():
    # Both the sync and streaming Responses paths must go through the null-safe counter,
    # not subtract usage.input_tokens_details.cached_tokens inline (TypeError when it is null).
    source = (ROOT / "processor/conversation/openai/utils.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for name in ("responses_completion_with_backoff", "responses_chat_completion_with_backoff"):
        function = next(
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
        )
        called = {
            node.func.id for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        attributes = {node.attr for node in ast.walk(function) if isinstance(node, ast.Attribute)}
        assert "get_responses_usage_token_counts" in called, name
        assert "cached_tokens" not in attributes, name
