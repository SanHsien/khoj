"""Anthropic request shape and prompt-cache usage accounting.

Why this exists: Claude Opus 4.7+ and every Claude 5.x model return a 400 for a manual
`thinking.budget_tokens`, for a non-default `temperature`, and for a final assistant
prefill; Opus 4.6 and Sonnet 4.6 already reject the prefill. The seeded default models
(`claude-sonnet-4-0`, `claude-3-5-haiku-latest`) were retired and return a 404
(docs/DECISIONS.md 2026-11-22). These tests pin that the request builders send none of
those fields to current models, and still send them to older models that accept them.

How: AST-load the product functions (no Django, torch or provider SDK import) and run
them against a stand-in client that records the request.

Cache tests also run the real usage accumulator for sync, streaming and operator
calls. Each cache counter independently covers missing, None, zero and positive
values, and must add to existing usage without losing or swapping cache tokens.
"""

import ast
import asyncio
import json
import logging
import re
from pathlib import Path
from time import perf_counter
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
        self.messages = self
        self.usage = SimpleNamespace(
            input_tokens=1, output_tokens=1, cache_read_input_tokens=0, cache_creation_input_tokens=0
        )

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
        return SimpleNamespace(content=[], usage=self.usage, model_dump_json=lambda: "{}")

    async def create(self, **kwargs):
        return self.get_final_message()


class AsyncRecorder(Recorder):
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def __aiter__(self):
        for chunk in self:
            yield chunk

    async def get_final_message(self):
        return super().get_final_message()


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
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", "") == "default_anthropic_chat_models" for t in node.targets)
    )
    assert defaults and not RETIRED & set(defaults)


def load_method(relative_path, class_name, method_name, namespace):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name
    )
    future = ast.parse("from __future__ import annotations").body
    exec(compile(ast.Module(body=future + [method], type_ignores=[]), relative_path, "exec"), namespace)
    return namespace[method_name]


@pytest.fixture
def cache_accounting(mod):
    """Run real accounting and adapter bodies; replace provider transport and pricing only."""
    namespace = dict(mod)
    namespace.update(
        logger=logging.getLogger(__name__),
        perf_counter=perf_counter,
        get_cost_of_chat_message=lambda *args, **kwargs: 0.0,
    )
    load("utils/helpers.py", ["get_chat_usage_metrics"], namespace)
    load(UTILS, ["anthropic_completion_with_backoff", "anthropic_chat_completion_with_backoff"], namespace)
    namespace["operator_call"] = load_method(
        "processor/operator/operator_agent_anthropic.py", "AnthropicOperatorAgent", "_call_model", namespace
    )
    namespace["update_usage"] = load_method(
        "processor/operator/operator_agent_base.py", "OperatorAgent", "_update_usage", namespace
    )
    return namespace


# Each counter varies independently, including a truly absent attribute.
CACHE_CASES = ["missing", None, 0, 17]


def check_cache_accounting(namespace, path, read, write):
    recorder = AsyncRecorder() if path == "stream" else Recorder()
    recorder.usage = SimpleNamespace(input_tokens=11, output_tokens=5)
    for field, value in [("cache_read_input_tokens", read), ("cache_creation_input_tokens", write)]:
        if value != "missing":
            setattr(recorder.usage, field, value)
    namespace["anthropic_clients"] = {None: recorder}
    namespace["anthropic_async_clients"] = {None: recorder}
    namespace["get_anthropic_async_client"] = lambda *args: recorder
    tracer = {
        "usage": {
            "input_tokens": 2,
            "output_tokens": 3,
            "cache_read_tokens": 7,
            "cache_write_tokens": 13,
            "thought_tokens": 0,
            "cost": 0.0,
        }
    }
    messages = [SimpleNamespace(role="user", content="hi")]
    model = "claude-haiku-4-5"
    if path == "sync":
        result = namespace["anthropic_completion_with_backoff"](messages, "", model, tracer=tracer)
        assert result.text == "ok"
    elif path == "stream":

        async def consume():
            return [
                part
                async for part in namespace["anthropic_chat_completion_with_backoff"](
                    messages, model, 0.4, None, "", tracer=tracer
                )
            ]

        assert [part.text for part in asyncio.run(consume())] == ["ok"]
    else:
        agent = SimpleNamespace(
            tracer=tracer, vision_model=SimpleNamespace(name=model), _format_message_for_api=lambda messages: messages
        )
        agent._update_usage = lambda *args: namespace["update_usage"](agent, *args)
        config = SimpleNamespace(name=model, ai_model_api=SimpleNamespace(api_key=None, api_base_url=""))
        assert asyncio.run(namespace["operator_call"](agent, messages, config, "")) == []
    assert tracer["usage"] == {
        "input_tokens": 13,
        "output_tokens": 8,
        "thought_tokens": 0,
        "cost": 0.0,
        "cache_read_tokens": 7 + (17 if read == 17 else 0),
        "cache_write_tokens": 13 + (17 if write == 17 else 0),
    }


@pytest.mark.parametrize("read", CACHE_CASES, ids=["missing", "none", "zero", "positive"])
@pytest.mark.parametrize("write", CACHE_CASES, ids=["missing", "none", "zero", "positive"])
def test_sync_cache_token_totals(cache_accounting, read, write):
    check_cache_accounting(cache_accounting, "sync", read, write)


@pytest.mark.parametrize("read", CACHE_CASES, ids=["missing", "none", "zero", "positive"])
@pytest.mark.parametrize("write", CACHE_CASES, ids=["missing", "none", "zero", "positive"])
def test_stream_cache_token_totals(cache_accounting, read, write):
    check_cache_accounting(cache_accounting, "stream", read, write)


@pytest.mark.parametrize("read", CACHE_CASES, ids=["missing", "none", "zero", "positive"])
@pytest.mark.parametrize("write", CACHE_CASES, ids=["missing", "none", "zero", "positive"])
def test_operator_cache_token_totals(cache_accounting, read, write):
    check_cache_accounting(cache_accounting, "operator", read, write)
