"""Anthropic request shape for current Claude models.

Why this exists: Claude Opus 4.7+ and every Claude 5.x model return a 400 for a manual
`thinking.budget_tokens`, for a non-default `temperature`, and for a final assistant
prefill; Opus 4.6 and Sonnet 4.6 already reject the prefill. The seeded default models
(`claude-sonnet-4-0`, `claude-3-5-haiku-latest`) were retired and return a 404
(docs/DECISIONS.md 2026-11-22). These tests pin that the request builders send none of
those fields to current models, and still send them to older models that accept them.

How: AST-load the product functions (no Django, torch or provider SDK import) and run
them against a stand-in client that records the request.
"""

import ast
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src/khoj"
UTILS = "processor/conversation/anthropic/utils.py"
RETIRED = {"claude-sonnet-4-0", "claude-sonnet-4-20250514", "claude-3-5-haiku-latest", "claude-3-5-haiku-20241022"}


def load(relative_path, names, namespace):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    selected, found = [], set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            node.decorator_list = []
            selected.append(node)
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            targets = {t.id for t in node.targets if isinstance(t, ast.Name)}
            if targets & set(names):
                selected.append(node)
                found |= targets & set(names)
    assert set(names) <= found, set(names) - found
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.Module(body=future + selected, type_ignores=[]), relative_path, "exec"), namespace)
    return namespace


class Recorder:
    def __init__(self):
        self.sent = {}
        self.beta = SimpleNamespace(messages=self)

    def stream(self, **kwargs):
        self.sent = kwargs
        return self

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def __iter__(self):
        yield SimpleNamespace(type="content_block_delta", delta=SimpleNamespace(type="text_delta", text="ok"))

    def get_final_message(self):
        usage = SimpleNamespace(input_tokens=1, output_tokens=1, cache_read_input_tokens=0, cache_creation_input_tokens=0)
        return SimpleNamespace(content=[], usage=usage)


@pytest.fixture(scope="module")
def mod():
    recorder = Recorder()
    namespace = {
        "re": re,
        "json": json,
        "Dict": dict,
        "anthropic": SimpleNamespace(types=SimpleNamespace(MessageParam=dict, ToolParam=dict)),
        "anthropic_clients": {},
        "get_anthropic_client": lambda key, base: recorder,
        "format_messages_for_anthropic": lambda messages, system_prompt: (list(messages), None),
        "get_chat_usage_metrics": lambda *a, **k: {},
        "is_none_or_empty": lambda value: not value,
        "is_promptrace_enabled": lambda: False,
        "ResponseWithThought": lambda **kw: SimpleNamespace(**kw),
    }
    names = [
        "DEFAULT_MAX_TOKENS_ANTHROPIC",
        "MAX_REASONING_TOKENS_ANTHROPIC",
        "REASONING_MODELS",
        "ADAPTIVE_THINKING_MODEL_PATTERN",
        "PREFILL_REJECTED_MODEL_PATTERN",
        "is_reasoning_model",
        "is_adaptive_thinking_model",
        "rejects_assistant_prefill",
        "anthropic_completion_with_backoff",
    ]
    load(UTILS, names, namespace)
    namespace["recorder"] = recorder
    return namespace


def send(mod, model, **kwargs):
    message = SimpleNamespace(role="user", content="hi")
    mod["anthropic_completion_with_backoff"]([message], "", model, temperature=0.4, tracer={}, **kwargs)
    return mod["recorder"].sent


@pytest.mark.parametrize("model", ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-4-7"])
def test_current_models_get_no_temperature_budget_or_prefill(mod, model):
    sent = send(mod, model, response_type="json_object", deepthought=True)
    assert "temperature" not in sent
    assert sent["thinking"] == {"type": "adaptive"}
    assert not any(isinstance(m, dict) and m.get("role") == "assistant" for m in sent["messages"])
    assert sent["max_tokens"] > mod["DEFAULT_MAX_TOKENS_ANTHROPIC"]


@pytest.mark.parametrize("model", ["claude-opus-4-6", "claude-sonnet-4-6"])
def test_four_six_models_get_no_prefill(mod, model):
    sent = send(mod, model, response_type="json_object")
    assert not any(isinstance(m, dict) and m.get("role") == "assistant" for m in sent["messages"])
    assert sent["temperature"] == 0.4


def test_older_reasoning_model_keeps_budget_and_temperature_one(mod):
    sent = send(mod, "claude-sonnet-4-5", deepthought=True)
    assert sent["thinking"] == {"type": "enabled", "budget_tokens": mod["MAX_REASONING_TOKENS_ANTHROPIC"]}
    assert sent["temperature"] == 1.0


def test_older_model_keeps_prefill_for_json(mod):
    sent = send(mod, "claude-haiku-4-5", response_type="json_object")
    assert sent["messages"][-1] == {"role": "assistant", "content": "{"}


def test_seeded_default_models_are_not_retired():
    tree = ast.parse((ROOT / "utils/constants.py").read_text(encoding="utf-8"))
    defaults = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == "default_anthropic_chat_models" for t in node.targets)
    )
    assert defaults and not RETIRED & set(defaults)
