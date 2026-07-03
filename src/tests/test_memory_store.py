"""Tests for the JSON filesystem memory store."""

from pathlib import Path

from memory import JsonMemoryStore, MemoryCategory, ProjectMemory


def test_loading_an_unknown_project_returns_empty_memory(tmp_path: Path) -> None:
        store = JsonMemoryStore(tmp_path)
        assert store.load("never-seen").is_empty()


def test_save_then_load_roundtrips_entries(tmp_path: Path) -> None:
        store = JsonMemoryStore(tmp_path)
        memory = (
                ProjectMemory.empty()
                .remember(MemoryCategory.COMMAND, "pytest -q")
                .remember(MemoryCategory.FILE, "app/main.py")
        )
        store.save("proj", memory)

        loaded = store.load("proj")
        assert [(e.category, e.content) for e in loaded.entries()] == [
                (MemoryCategory.COMMAND, "pytest -q"),
                (MemoryCategory.FILE, "app/main.py"),
        ]


def test_projects_are_keyed_independently(tmp_path: Path) -> None:
        store = JsonMemoryStore(tmp_path)
        store.save("a", ProjectMemory.empty().remember(MemoryCategory.SUMMARY, "about a"))
        store.save("b", ProjectMemory.empty().remember(MemoryCategory.SUMMARY, "about b"))

        assert [e.content for e in store.load("a").entries()] == ["about a"]
        assert [e.content for e in store.load("b").entries()] == ["about b"]


def test_a_path_like_project_id_is_sanitized_to_one_file(tmp_path: Path) -> None:
        store = JsonMemoryStore(tmp_path)
        store.save("/home/me/repos/app", ProjectMemory.empty().remember(MemoryCategory.BUG, "x"))

        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1  # no nested directories created from the slashes
        assert [e.content for e in store.load("/home/me/repos/app").entries()] == ["x"]


def test_an_unknown_category_in_a_file_is_skipped_not_fatal(tmp_path: Path) -> None:
        (tmp_path / "proj.json").write_text(
                '[{"category": "made-up", "content": "x"}, '
                '{"category": "command", "content": "pytest"}]',
                encoding="utf-8",
        )
        loaded = JsonMemoryStore(tmp_path).load("proj")
        assert [e.content for e in loaded.entries()] == ["pytest"]
