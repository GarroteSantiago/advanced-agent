"""Tests for the pure ProjectMemory aggregate."""

from memory import MemoryCategory, ProjectMemory


def test_empty_memory_has_no_entries_and_a_blank_briefing() -> None:
        memory = ProjectMemory.empty()
        assert memory.is_empty()
        assert memory.entries() == ()
        assert memory.brief() == ""


def test_remember_appends_without_mutating_the_original() -> None:
        original = ProjectMemory.empty()
        grown = original.remember(MemoryCategory.COMMAND, "pytest -q")

        assert original.is_empty()  # copy-on-write: the original is untouched
        assert [e.content for e in grown.entries()] == ["pytest -q"]


def test_remember_suppresses_exact_duplicates() -> None:
        memory = (
                ProjectMemory.empty()
                .remember(MemoryCategory.COMMAND, "pytest -q")
                .remember(MemoryCategory.COMMAND, "pytest -q")
        )
        assert len(memory.entries()) == 1


def test_remember_ignores_blank_content() -> None:
        memory = ProjectMemory.empty().remember(MemoryCategory.SUMMARY, "   ")
        assert memory.is_empty()


def test_entries_can_be_filtered_by_category() -> None:
        memory = (
                ProjectMemory.empty()
                .remember(MemoryCategory.COMMAND, "pytest -q")
                .remember(MemoryCategory.FILE, "app/main.py")
        )
        commands = memory.entries(MemoryCategory.COMMAND)
        assert [e.content for e in commands] == ["pytest -q"]


def test_brief_groups_entries_under_category_headings() -> None:
        memory = (
                ProjectMemory.empty()
                .remember(MemoryCategory.COMMAND, "pytest -q")
                .remember(MemoryCategory.FILE, "app/main.py")
        )
        brief = memory.brief()

        assert "## Commands" in brief
        assert "- pytest -q" in brief
        assert "## Files" in brief
        assert "- app/main.py" in brief
        # Empty categories are omitted.
        assert "## Architecture" not in brief
