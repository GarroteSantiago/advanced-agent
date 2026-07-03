"""Tests for estimated token cost."""

from __future__ import annotations

from llm import TokenUsage, estimate_cost


def test_known_model_costs_prompt_and_completion_tokens() -> None:
        usage = TokenUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)

        # gpt-5-nano rates: (0.05, 0.40) USD per 1M tokens.
        assert estimate_cost("gpt-5-nano", usage) == 0.45


def test_unknown_model_costs_zero() -> None:
        usage = TokenUsage(prompt_tokens=1_000, completion_tokens=1_000)
        assert estimate_cost("no-such-model", usage) == 0.0


def test_zero_usage_costs_zero() -> None:
        assert estimate_cost("gpt-5-nano", TokenUsage()) == 0.0
