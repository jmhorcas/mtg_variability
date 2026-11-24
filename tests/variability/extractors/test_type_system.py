
"""Tests for the MTG type system extractor and parser."""

import pytest

from mtg_variability.variability.extractors.type_system import (
    ParsedTypeLine,
    TypeLineParser,
    TypeSystemExtractor,
)
from mtg_variability.variability.taxonomy import (
    MTGTaxonomy,
    SubtypeCategory,
    SubtypeCategoryDefinition,
)


@pytest.fixture
def taxonomy() -> MTGTaxonomy:
    """Build a small taxonomy covering the relevant parsing cases."""
    categories = {
        SubtypeCategory.ARTIFACT: SubtypeCategoryDefinition(
            category=SubtypeCategory.ARTIFACT,
            card_types=("Artifact",),
            values=("Equipment", "Vehicle", "Spacecraft"),
        ),
        SubtypeCategory.ENCHANTMENT: SubtypeCategoryDefinition(
            category=SubtypeCategory.ENCHANTMENT,
            card_types=("Enchantment",),
            values=("Aura", "Saga"),
        ),
        SubtypeCategory.LAND: SubtypeCategoryDefinition(
            category=SubtypeCategory.LAND,
            card_types=("Land",),
            values=("Forest", "Island", "Plains"),
        ),
        SubtypeCategory.PLANESWALKER: SubtypeCategoryDefinition(
            category=SubtypeCategory.PLANESWALKER,
            card_types=("Planeswalker",),
            values=("Jace", "Chandra"),
        ),
        SubtypeCategory.SPELL: SubtypeCategoryDefinition(
            category=SubtypeCategory.SPELL,
            card_types=("Instant", "Sorcery"),
            values=("Arcane", "Lesson"),
        ),
        SubtypeCategory.CREATURE: SubtypeCategoryDefinition(
            category=SubtypeCategory.CREATURE,
            card_types=("Creature", "Kindred"),
            values=("Human", "Wizard", "Golem", "Time Lord"),
        ),
        SubtypeCategory.PLANAR: SubtypeCategoryDefinition(
            category=SubtypeCategory.PLANAR,
            card_types=("Plane",),
            values=("Serra’s Realm", "Spacecraft"),
        ),
        SubtypeCategory.DUNGEON: SubtypeCategoryDefinition(
            category=SubtypeCategory.DUNGEON,
            card_types=("Dungeon",),
            values=("Undercity",),
        ),
        SubtypeCategory.BATTLE: SubtypeCategoryDefinition(
            category=SubtypeCategory.BATTLE,
            card_types=("Battle",),
            values=("Siege",),
        ),
    }

    return MTGTaxonomy(
        rules_version="20261106",
        rules_effective_date="2026-11-06",
        source_file="MagicCompRules 20261106.txt",
        card_types=(
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
        ),
        supertypes=(
            "Basic",
            "Legendary",
            "Ongoing",
            "Snow",
            "World",
        ),
        card_types_without_subtypes=(
            "Conspiracy",
            "Phenomenon",
            "Scheme",
            "Vanguard",
        ),
        subtype_categories=categories,
    )


@pytest.fixture
def parser(taxonomy: MTGTaxonomy) -> TypeLineParser:
    """Return a parser configured with the test taxonomy."""
    return TypeLineParser(taxonomy)


@pytest.fixture
def extractor(taxonomy: MTGTaxonomy) -> TypeSystemExtractor:
    """Return a type system extractor configured with the test taxonomy."""
    return TypeSystemExtractor(taxonomy)


def _find_child(point, name: str):
    """Find a direct child variation point by name."""
    return next(
        (child for child in point.child_points if child.name == name),
        None,
    )


def _find_variant(point, name: str):
    """Find a variant by name."""
    return next(
        (variant for variant in point.variants if variant.name == name),
        None,
    )


# ---------------------------------------------------------------------------
# TypeLineParser
# ---------------------------------------------------------------------------


def test_parse_empty_type_line(parser: TypeLineParser) -> None:
    """Return an empty result for an empty type line."""
    parsed = parser.parse("")

    assert isinstance(parsed, ParsedTypeLine)
    assert parsed.is_empty
    assert not parsed.supertypes
    assert not parsed.card_types
    assert not parsed.subtypes


def test_parse_type_line_with_only_card_type(
    parser: TypeLineParser,
) -> None:
    """Parse a type line without subtypes."""
    parsed = parser.parse("Artifact")

    assert parsed.card_types == {"Artifact"}
    assert not parsed.supertypes
    assert not parsed.subtypes
    assert parsed.is_empty is False


def test_parse_supertypes_and_multiple_card_types(
    parser: TypeLineParser,
) -> None:
    """Recognize multiple supertypes and card types."""
    parsed = parser.parse(
        "Legendary Snow Artifact Creature — Golem"
    )

    assert parsed.supertypes == {"Legendary", "Snow"}
    assert parsed.card_types == {"Artifact", "Creature"}
    assert set(parsed.subtypes) == {
        (SubtypeCategory.CREATURE, "Golem"),
    }


def test_parse_subtypes_by_category(
    parser: TypeLineParser,
) -> None:
    """Associate each subtype with its correct category."""
    parsed = parser.parse(
        "Artifact Creature — Equipment Golem"
    )

    assert set(parsed.subtypes) == {
        (SubtypeCategory.ARTIFACT, "Equipment"),
        (SubtypeCategory.CREATURE, "Golem"),
    }


def test_parse_multi_word_creature_subtype(
    parser: TypeLineParser,
) -> None:
    """Recognize the two-word creature subtype Time Lord."""
    parsed = parser.parse("Creature — Time Lord")

    assert parsed.subtypes == (
        (SubtypeCategory.CREATURE, "Time Lord"),
    )
    assert not parsed.unknown_subtypes


def test_parse_multi_word_planar_subtype(
    parser: TypeLineParser,
) -> None:
    """Recognize a multi-word planar subtype with Unicode punctuation."""
    parsed = parser.parse("Plane — Serra’s Realm")

    assert parsed.subtypes == (
        (SubtypeCategory.PLANAR, "Serra’s Realm"),
    )
    assert not parsed.unknown_subtypes


def test_parse_shared_subtype_using_card_type_context(
    parser: TypeLineParser,
) -> None:
    """Resolve a shared subtype using its associated card type."""
    artifact = parser.parse("Artifact — Spacecraft")
    plane = parser.parse("Plane — Spacecraft")

    assert artifact.subtypes == (
        (SubtypeCategory.ARTIFACT, "Spacecraft"),
    )
    assert plane.subtypes == (
        (SubtypeCategory.PLANAR, "Spacecraft"),
    )


def test_parse_multiple_card_types_with_shared_subtype(
    parser: TypeLineParser,
) -> None:
    """Resolve a subtype when multiple card types are present."""
    parsed = parser.parse("Artifact Creature — Spacecraft")

    assert parsed.subtypes == (
        (SubtypeCategory.ARTIFACT, "Spacecraft"),
    )


def test_parse_en_dash_separator(parser: TypeLineParser) -> None:
    """Accept an en dash as a type/subtype separator."""
    parsed = parser.parse("Creature – Human")

    assert parsed.subtypes == (
        (SubtypeCategory.CREATURE, "Human"),
    )


def test_parse_case_insensitively(
    parser: TypeLineParser,
) -> None:
    """Recognize type names and subtypes regardless of input casing."""
    parsed = parser.parse("legendary creature — time lord")

    assert parsed.supertypes == {"Legendary"}
    assert parsed.card_types == {"Creature"}
    assert parsed.subtypes == (
        (SubtypeCategory.CREATURE, "Time Lord"),
    )


def test_parse_unknown_prefix_value(
    parser: TypeLineParser,
) -> None:
    """Preserve unrecognized values before the subtype separator."""
    parsed = parser.parse(
        "Legendary Future Artifact — Equipment"
    )

    assert parsed.supertypes == {"Legendary"}
    assert parsed.card_types == {"Artifact"}
    assert parsed.unknown_prefix_values == ("Future",)


def test_parse_unknown_subtype(
    parser: TypeLineParser,
) -> None:
    """Preserve subtypes not present in the taxonomy."""
    parsed = parser.parse("Artifact — Equipment Contraption")

    assert parsed.subtypes == (
        (SubtypeCategory.ARTIFACT, "Equipment"),
    )
    assert parsed.unknown_subtypes == ("Contraption",)


def test_parse_type_line_without_applicable_subtype_category(
    parser: TypeLineParser,
) -> None:
    """Preserve subtype tokens when no category applies to the card type."""
    parsed = parser.parse("Conspiracy — Unknown")

    assert parsed.card_types == {"Conspiracy"}
    assert not parsed.subtypes
    assert parsed.unknown_subtypes == ("Unknown",)


def test_parse_multi_face_type_line(
    parser: TypeLineParser,
) -> None:
    """Combine recognized values from all faces of a card."""
    parsed = parser.parse(
        "Creature — Human // Creature — Wizard"
    )

    assert parsed.card_types == {"Creature"}
    assert set(parsed.subtypes) == {
        (SubtypeCategory.CREATURE, "Human"),
        (SubtypeCategory.CREATURE, "Wizard"),
    }


def test_parse_deduplicates_values_across_faces(
    parser: TypeLineParser,
) -> None:
    """Do not duplicate identical values appearing on multiple faces."""
    parsed = parser.parse(
        "Creature — Human // Creature — Human"
    )

    assert parsed.subtypes == (
        (SubtypeCategory.CREATURE, "Human"),
    )


def test_parse_rejects_non_string_input(
    parser: TypeLineParser,
) -> None:
    """Reject values that are not strings."""
    with pytest.raises(TypeError):
        parser.parse(None)


# ---------------------------------------------------------------------------
# TypeSystemExtractor
# ---------------------------------------------------------------------------


def test_extractor_name(extractor: TypeSystemExtractor) -> None:
    """Expose a stable registry name."""
    assert extractor.name == "type-system:type"


def test_extractor_returns_empty_for_empty_dataset(
    extractor: TypeSystemExtractor,
) -> None:
    """Return no variation points for an empty dataset."""
    assert extractor.extract([]) == ()


def test_extractor_builds_type_hierarchy(
    extractor: TypeSystemExtractor,
) -> None:
    """Build the root type point and its semantic children."""
    records = [
        {
            "name": "Card A",
            "type": "Legendary Artifact Creature — Golem",
        },
        {
            "name": "Card B",
            "type": "Artifact — Equipment",
        },
        {
            "name": "Card C",
            "type": "Creature — Human",
        },
    ]

    result = extractor.extract(records)

    assert len(result) == 1

    root = result[0]

    assert root.name == "type"
    assert root.total_observations == 3
    assert root.missing_observations == 0

    child_names = {child.name for child in root.child_points}

    assert child_names == {
        "supertypes",
        "card_types",
        "subtypes",
    }

    subtype_root = _find_child(root, "subtypes")

    assert subtype_root is not None

    subtype_names = {
        child.name for child in subtype_root.child_points
    }

    assert subtype_names == {
        "subtypes:artifact",
        "subtypes:creature",
    }


def test_extractor_counts_supertypes_and_card_types(
    extractor: TypeSystemExtractor,
) -> None:
    """Count each distinct type value once per card."""
    records = [
        {
            "name": "Card A",
            "type": "Legendary Artifact Creature — Golem",
        },
        {
            "name": "Card B",
            "type": "Legendary Creature — Human",
        },
        {
            "name": "Card C",
            "type": "Basic Land — Forest",
        },
    ]

    root = extractor.extract(records)[0]

    supertypes = _find_child(root, "supertypes")
    card_types = _find_child(root, "card_types")

    assert supertypes is not None
    assert card_types is not None

    legendary = _find_variant(supertypes, "Legendary")
    creature = _find_variant(card_types, "Creature")
    artifact = _find_variant(card_types, "Artifact")
    land = _find_variant(card_types, "Land")

    assert legendary is not None
    assert legendary.occurrences == 2

    assert creature is not None
    assert creature.occurrences == 2

    assert artifact is not None
    assert artifact.occurrences == 1

    assert land is not None
    assert land.occurrences == 1


def test_extractor_counts_subtypes_by_category(
    extractor: TypeSystemExtractor,
) -> None:
    """Count subtypes in their corresponding category."""
    records = [
        {
            "name": "Card A",
            "type": "Artifact Creature — Equipment Golem",
        },
        {
            "name": "Card B",
            "type": "Artifact — Equipment",
        },
        {
            "name": "Card C",
            "type": "Creature — Human",
        },
    ]

    root = extractor.extract(records)[0]
    subtype_root = _find_child(root, "subtypes")

    assert subtype_root is not None

    artifact_point = _find_child(
        subtype_root,
        "subtypes:artifact",
    )
    creature_point = _find_child(
        subtype_root,
        "subtypes:creature",
    )

    assert artifact_point is not None
    assert creature_point is not None

    equipment = _find_variant(artifact_point, "Equipment")
    golem = _find_variant(creature_point, "Golem")
    human = _find_variant(creature_point, "Human")

    assert equipment is not None
    assert equipment.occurrences == 2

    assert golem is not None
    assert golem.occurrences == 1

    assert human is not None
    assert human.occurrences == 1


def test_extractor_does_not_duplicate_subtypes_per_card(
    extractor: TypeSystemExtractor,
) -> None:
    """Count a subtype only once when it appears on multiple faces."""
    records = [
        {
            "name": "Card A",
            "type": "Creature — Human // Creature — Human",
        },
        {
            "name": "Card B",
            "type": "Creature — Human",
        },
    ]

    root = extractor.extract(records)[0]
    subtype_root = _find_child(root, "subtypes")
    assert subtype_root is not None

    creature_point = _find_child(
        subtype_root,
        "subtypes:creature",
    )
    assert creature_point is not None

    human = _find_variant(creature_point, "Human")

    assert human is not None
    assert human.occurrences == 2


def test_extractor_counts_category_observations_and_missing_subtypes(
    extractor: TypeSystemExtractor,
) -> None:
    """Count missing subtypes only for applicable card categories."""
    records = [
        {
            "name": "Card A",
            "type": "Artifact — Equipment",
        },
        {
            "name": "Card B",
            "type": "Artifact",
        },
        {
            "name": "Card C",
            "type": "Creature — Human",
        },
        {
            "name": "Card D",
            "type": "Creature",
        },
    ]

    root = extractor.extract(records)[0]
    subtype_root = _find_child(root, "subtypes")
    assert subtype_root is not None

    artifact_point = _find_child(
        subtype_root,
        "subtypes:artifact",
    )
    creature_point = _find_child(
        subtype_root,
        "subtypes:creature",
    )

    assert artifact_point is not None
    assert creature_point is not None

    assert artifact_point.total_observations == 2
    assert artifact_point.missing_observations == 1

    assert creature_point.total_observations == 2
    assert creature_point.missing_observations == 1


def test_extractor_records_unknown_values_in_metadata(
    extractor: TypeSystemExtractor,
) -> None:
    """Expose unrecognized values without discarding them."""
    records = [
        {
            "name": "Card A",
            "type": "Future Artifact — Contraption",
        },
        {
            "name": "Card B",
            "type": "Artifact — Contraption",
        },
    ]

    root = extractor.extract(records)[0]

    assert root.metadata["unknown_prefix_values"] == {
        "Future": 1,
    }
    assert root.metadata["unknown_subtypes"] == {
        "Contraption": 2,
    }


def test_extractor_tracks_missing_type_lines(
    extractor: TypeSystemExtractor,
) -> None:
    """Count missing type lines at the root level."""
    records = [
        {
            "name": "Card A",
            "type": "Creature — Human",
        },
        {
            "name": "Card B",
            "type": "",
        },
        {
            "name": "Card C",
            "type": "   ",
        },
    ]

    root = extractor.extract(records)[0]

    assert root.total_observations == 3
    assert root.missing_observations == 2


def test_extractor_keeps_unknown_only_type_lines(
    extractor: TypeSystemExtractor,
) -> None:
    """Do not classify a non-empty unrecognized type line as missing."""
    records = [
        {
            "name": "Card A",
            "type": "Future",
        },
        {
            "name": "Card B",
            "type": "Artifact — Equipment",
        },
    ]

    root = extractor.extract(records)[0]

    assert root.total_observations == 2
    assert root.missing_observations == 0
    assert root.metadata["unknown_prefix_values"] == {
        "Future": 1,
    }


def test_extractor_respects_max_examples(
    taxonomy: MTGTaxonomy,
) -> None:
    """Limit the number of examples stored for each variant."""
    extractor = TypeSystemExtractor(
        taxonomy,
        max_examples=2,
    )

    records = [
        {"name": "Card A", "type": "Creature — Human"},
        {"name": "Card B", "type": "Creature — Human"},
        {"name": "Card C", "type": "Creature — Human"},
    ]

    root = extractor.extract(records)[0]
    card_types = _find_child(root, "card_types")

    assert card_types is not None

    creature = _find_variant(card_types, "Creature")

    assert creature is not None
    assert creature.occurrences == 3
    assert creature.examples == ("Card A", "Card B")


def test_extractor_handles_missing_example_attribute(
    extractor: TypeSystemExtractor,
) -> None:
    """Extract type variability when card names are unavailable."""
    records = [
        {"type": "Creature — Human"},
        {"type": "Creature — Wizard"},
    ]

    root = extractor.extract(records)[0]
    card_types = _find_child(root, "card_types")

    assert card_types is not None

    creature = _find_variant(card_types, "Creature")

    assert creature is not None
    assert creature.occurrences == 2
    assert creature.examples == ()


def test_extractor_rejects_invalid_configuration(
    taxonomy: MTGTaxonomy,
) -> None:
    """Reject invalid attribute names and example limits."""
    with pytest.raises(ValueError):
        TypeSystemExtractor(taxonomy, attribute=" ")

    with pytest.raises(ValueError):
        TypeSystemExtractor(taxonomy, example_attribute=" ")

    with pytest.raises(ValueError):
        TypeSystemExtractor(taxonomy, max_examples=0)

    with pytest.raises(ValueError):
        TypeSystemExtractor(taxonomy, max_examples=True)
