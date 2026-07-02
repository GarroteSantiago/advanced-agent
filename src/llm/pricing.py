"""Estimated token cost per model.

A deliberately small, updatable lookup: the spec requires recording an
*estimated* cost, not billing-grade accuracy. Rates are USD per 1M tokens,
split into prompt/completion. Unknown models cost 0.0 (better an honest zero
than a wrong number); update ``_RATES`` when the model or its pricing changes.
"""

from __future__ import annotations

from llm.messages import TokenUsage

_PER_MILLION = 1_000_000

# (prompt, completion) USD per 1M tokens -- approximate, update as needed.
_RATES: dict[str, tuple[float, float]] = {
        "gpt-5-nano": (0.05, 0.40),
        "gpt-5-mini": (0.25, 2.00),
        "gpt-5": (1.25, 10.00),
}


def estimate_cost(model: str, usage: TokenUsage) -> float:
        rate = _RATES.get(model)
        if rate is None:
                return 0.0
        prompt_rate, completion_rate = rate
        prompt_cost = usage.prompt_tokens * prompt_rate
        completion_cost = usage.completion_tokens * completion_rate
        return (prompt_cost + completion_cost) / _PER_MILLION
