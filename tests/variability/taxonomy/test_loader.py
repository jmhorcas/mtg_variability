
"""Tests for the MTG taxonomy loader."""

import json
from pathlib import Path

import pytest

from mtg_variability.variability.taxonomy import (
    SubtypeCategory,
    TaxonomyLoadError,
    load_taxonomy,
)


CARD_TYPES = [
    "Artifact",
    "Battle",
    "Conspiracy",
    "Creature",
    "Dungeon",
    "Enchantment",
    "Instant",
    "Kindred",
    "Land",
    "Phenomenon",
    "Plane",
    "Planeswalker",
    "Scheme",
    "Sorcery",
    "Vanguard",
]


def _valid_taxonomy_data() -> dict:
    """Build a minimal valid taxonomy document."""
    return {
        "metadata": {
            "rules_version": "20261106",
            "rules_effective_date": "2026-11-06",
            "source_file": "MagicCompRules 20261106.txt",
        },
        "card_types": CARD_TYPES,
        "supertypes": [
            "Basic",
            "Legendary",
            "Ongoing",
            "Snow",
            "World",
        ],
        "card_types_without_subtypes": [
            "Conspiracy",
            "Phenomenon",
            "Scheme",
            "Vanguard",
        ],
        "subtype_categories": {
            "artifact": {
                "card_types": ["Artifact"],
                "values": ["Equipment", "Vehicle", "Spacecraft"],
            },
            "enchantment": {
                "card_types": ["Enchantment"],
                "values": ["Aura", "Saga"],
            },
            "land": {
                "card_types": ["Land"],
                "values": ["Forest", "Island"],
            },
            "planeswalker": {
                "card_types": ["Planeswalker"],
                "values": ["Jace"],
            },
            "spell": {
                "card_types": ["Instant", "Sorcery"],
                "values": ["Arcane", "Lesson"],
            },
            "creature": {
                "card_types": ["Creature", "Kindred"],
                "values": ["Human", "Time Lord"],
            },
            "planar": {
                "card_types": ["Plane"],
                "values": ["Serra’s Realm", "Spacecraft"],
            },
            "dungeon": {
                "card_types": ["Dungeon"],
                "values": ["Undercity"],
            },
            "battle": {
                "card_types": ["Battle"],
                "values": ["Siege"],
            },
        },
    }


def _write_json(path: Path, data: dict) -> None:
    """Write a JSON document to a temporary path."""
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_load_valid_taxonomy(tmp_path: Path) -> None:
    """Load a valid taxonomy document."""
    source = tmp_path / "taxonomy.json"
    _write_json(source, _valid_taxonomy_data())

    taxonomy = load_taxonomy(source)

    assert taxonomy.rules_version == "20261106"
    assert taxonomy.rules_effective_date == "2026-11-06"
    assert taxonomy.is_card_type("artifact")
    assert taxonomy.is_supertype("legendary")
    assert taxonomy.is_subtype("Equipment")


def test_load_taxonomy_preserves_unicode(tmp_path: Path) -> None:
    """Preserve Unicode characters in subtype names."""
    source = tmp_path / "taxonomy.json"
    _write_json(source, _valid_taxonomy_data())

    taxonomy = load_taxonomy(source)

    planar_subtypes = taxonomy.get_subtypes(SubtypeCategory.PLANAR)

    assert "Serra’s Realm" in planar_subtypes


def test_load_taxonomy_preserves_ambiguous_subtypes(
    tmp_path: Path,
) -> None:
    """Preserve subtypes associated with multiple categories."""
    source = tmp_path / "taxonomy.json"
    _write_json(source, _valid_taxonomy_data())

    taxonomy = load_taxonomy(source)

    match = taxonomy.get_subtype_match("Spacecraft")

    assert match is not None
    assert match.is_ambiguous
    assert set(match.categories) == {
        SubtypeCategory.ARTIFACT,
        SubtypeCategory.PLANAR,
    }


def test_load_taxonomy_is_case_insensitive(tmp_path: Path) -> None:
    """Perform case-insensitive taxonomy lookups."""
    source = tmp_path / "taxonomy.json"
    _write_json(source, _valid_taxonomy_data())

    taxonomy = load_taxonomy(source)

    assert taxonomy.is_card_type("artifact")
    assert taxonomy.is_supertype("LEGENDARY")
    assert taxonomy.is_subtype("equipment")


def test_load_missing_file_raises_file_not_found_error(
    tmp_path: Path,
) -> None:
    """Propagate missing-file errors."""
    source = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_taxonomy(source)


def test_load_invalid_json_raises_taxonomy_load_error(
    tmp_path: Path,
) -> None:
    """Reject malformed JSON documents."""
    source = tmp_path / "taxonomy.json"
    source.write_text("{ invalid json", encoding="utf-8")

    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(source)


def test_load_taxonomy_rejects_missing_required_fields(
    tmp_path: Path,
) -> None:
    """Reject documents missing required root fields."""
    data = _valid_taxonomy_data()
    del data["card_types"]

    source = tmp_path / "taxonomy.json"
    _write_json(source, data)

    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(source)


def test_load_taxonomy_rejects_unknown_root_fields(
    tmp_path: Path,
) -> None:
    """Reject unexpected root fields."""
    data = _valid_taxonomy_data()
    data["unexpected"] = True

    source = tmp_path / "taxonomy.json"
    _write_json(source, data)

    with pytest.raises(TaxonomyLoadError):
        load_taxonomy(source)
