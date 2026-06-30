"""Smoke test: the top-level src/ packages import under the configured layout."""

import importlib


def test_top_level_packages_import():
        for name in ("harness", "agent", "llm", "memory", "prompts", "common"):
                assert importlib.import_module(name) is not None
