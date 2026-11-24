
"""Integration tests for the MTG taxonomy generator."""

import json
from pathlib import Path

import pytest

from mtg_variability.scripts.generate_taxonomy import (
    TaxonomyGenerationError,
    generate_taxonomy,
)
from mtg_variability.variability.taxonomy import (
    SubtypeCategory,
    load_taxonomy,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RULES_FILE = PROJECT_ROOT / "mtg_variability" / "data" / "MagicCompRules 20261106.txt"


@pytest.fixture
def rules_file() -> Path:
    """Return the project's Comprehensive Rules snapshot."""
    if not RULES_FILE.is_file():
        pytest.skip(
            f"Comprehensive Rules snapshot not found: {RULES_FILE}"
        )

    return RULES_FILE


def test_generate_taxonomy_from_comprehensive_rules(
    rules_file: Path,
    tmp_path: Path,
) -> None:
    """Generate a taxonomy from the official rules snapshot."""
    output = tmp_path / "taxonomy.json"

    result = generate_taxonomy(rules_file, output)

    assert result == output
    assert output.is_file()

    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["metadata"]["rules_effective_date"] == "2026-11-06"
    assert len(data["card_types"]) == 15
    assert len(data["supertypes"]) == 5
    assert len(data["card_types_without_subtypes"]) == 4
    assert len(data["subtype_categories"]) == 9


def test_generated_taxonomy_has_expected_subtype_counts(
    rules_file: Path,
    tmp_path: Path,
) -> None:
    """Check subtype counts against the reviewed rules snapshot."""
    output = tmp_path / "taxonomy.json"
    generate_taxonomy(rules_file, output)

    data = json.loads(output.read_text(encoding="utf-8"))

    expected_counts = {
        "artifact": 24,
        "enchantment": 13,
        "land": 17,
        "planeswalker": 87,
        "spell": 5,
        "creature": 367,
        "planar": 82,
        "dungeon": 1,
        "battle": 1,
    }

    actual_counts = {
        name: len(definition["values"])
        for name, definition in data["subtype_categories"].items()
    }

    assert actual_counts == expected_counts


def test_generated_taxonomy_preserves_special_subtypes(
    rules_file: Path,
    tmp_path: Path,
) -> None:
    """Check special subtype cases in the generated taxonomy."""
    output = tmp_path / "taxonomy.json"
    generate_taxonomy(rules_file, output)

    taxonomy = load_taxonomy(output)

    creature_subtypes = taxonomy.get_subtypes(
        SubtypeCategory.CREATURE
    )
    planar_subtypes = taxonomy.get_subtypes(
        SubtypeCategory.PLANAR
    )

    assert "Time Lord" in creature_subtypes
    assert "Serra’s Realm" in planar_subtypes

    spacecraft = taxonomy.get_subtype_match("Spacecraft")

    assert spacecraft is not None
    assert spacecraft.is_ambiguous
    assert set(spacecraft.categories) == {
        SubtypeCategory.ARTIFACT,
        SubtypeCategory.PLANAR,
    }


def test_generated_taxonomy_can_be_loaded(
    rules_file: Path,
    tmp_path: Path,
) -> None:
    """Verify compatibility between the generator and the loader."""
    output = tmp_path / "taxonomy.json"

    generate_taxonomy(rules_file, output)
    taxonomy = load_taxonomy(output)

    assert taxonomy.rules_effective_date == "2026-11-06"
    assert taxonomy.is_card_type("Creature")
    assert taxonomy.is_card_type("Kindred")
    assert taxonomy.is_supertype("Legendary")


def test_generation_is_deterministic(
    rules_file: Path,
    tmp_path: Path,
) -> None:
    """Generate identical JSON content from the same rules snapshot."""
    first_output = tmp_path / "first.json"
    second_output = tmp_path / "second.json"

    generate_taxonomy(rules_file, first_output)
    generate_taxonomy(rules_file, second_output)

    assert first_output.read_bytes() == second_output.read_bytes()


def test_generation_failure_does_not_overwrite_existing_output(
    tmp_path: Path,
) -> None:
    """Preserve an existing output when generation fails."""
    invalid_source = tmp_path / "invalid_rules.txt"
    output = tmp_path / "taxonomy.json"

    original_content = '{"existing": true}\n'

    invalid_source.write_text(
        "This is not a valid Comprehensive Rules document.",
        encoding="utf-8",
    )
    output.write_text(original_content, encoding="utf-8")

    with pytest.raises(TaxonomyGenerationError):
        generate_taxonomy(invalid_source, output)

    assert output.read_text(encoding="utf-8") == original_content
