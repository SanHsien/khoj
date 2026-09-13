from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from khoj.utils.security import is_exact_https_host, sanitize_log_value


def test_sanitize_log_value_escapes_record_delimiters() -> None:
    assert sanitize_log_value("safe\r\nforged") == r"safe\r\nforged"


def test_is_exact_https_host_rejects_lookalikes() -> None:
    assert is_exact_https_host("https://api.groq.com/openai/v1", "api.groq.com")
    assert not is_exact_https_host("https://api.groq.com.evil.example", "api.groq.com")
    assert not is_exact_https_host("https://api.groq.com@evil.example", "api.groq.com")
    assert not is_exact_https_host("http://api.groq.com", "api.groq.com")
