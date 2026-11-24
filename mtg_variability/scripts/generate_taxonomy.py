
"""Generate the MTG taxonomy JSON from the Comprehensive Rules."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCE = (
    PROJECT_ROOT
    #/ "mtg_variability"
    / "data"
    / "MagicCompRules 20261106.txt"
)

DEFAULT_OUTPUT = (
    PROJECT_ROOT
    #/ "mtg_variability"
    / "data"
    / "taxonomy.json"
)


CATEGORY_DEFINITIONS = {
    "artifact": {
        "card_types": ["Artifact"],
        "rule": "205.3g",
        "phrase": "The artifact types are ",
    },
    "enchantment": {
        "card_types": ["Enchantment"],
        "rule": "205.3h",
        "phrase": "The enchantment types are ",
    },
    "land": {
        "card_types": ["Land"],
        "rule": "205.3i",
        "phrase": "The land types are ",
    },
    "planeswalker": {
        "card_types": ["Planeswalker"],
        "rule": "205.3j",
        "phrase": "The planeswalker types are ",
    },
    "spell": {
        "card_types": ["Instant", "Sorcery"],
        "rule": "205.3k",
        "phrase": "The spell types are ",
    },
    "creature": {
        "card_types": ["Creature", "Kindred"],
        "rule": "205.3m",
        "phrase": "All other creature types are one word long: ",
    },
    "planar": {
        "card_types": ["Plane"],
        "rule": "205.3n",
        "phrase": "The planar types are ",
    },
    "dungeon": {
        "card_types": ["Dungeon"],
        "rule": "205.3p",
        "phrase": "That dungeon type is ",
    },
    "battle": {
        "card_types": ["Battle"],
        "rule": "205.3q",
        "phrase": "That battle type is ",
    },
}


class TaxonomyGenerationError(ValueError):
    """Raised when the Comprehensive Rules cannot be parsed safely."""


def generate_taxonomy(
    source_path: Path,
    output_path: Path,
) -> Path:
    """Generate a taxonomy JSON file from the Comprehensive Rules."""
    source_path = Path(source_path)
    output_path = Path(output_path)

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Comprehensive Rules file not found: {source_path}"
        )

    rules_text = source_path.read_text(encoding="utf-8-sig")

    taxonomy = _extract_taxonomy(
        rules_text=rules_text,
        source_file=source_path.name,
    )

    _write_json(taxonomy, output_path)
    return output_path


def _extract_taxonomy(
    rules_text: str,
    source_file: str,
) -> dict[str, Any]:
    """Extract and validate all taxonomy data."""
    effective_date = _extract_effective_date(rules_text)

    card_types = _extract_card_types(rules_text)
    supertypes = _extract_supertypes(rules_text)
    subtype_categories = _extract_subtype_categories(rules_text)
    card_types_without_subtypes = (
        _extract_card_types_without_subtypes(rules_text)
    )

    _validate_taxonomy(
        card_types=card_types,
        supertypes=supertypes,
        subtype_categories=subtype_categories,
        card_types_without_subtypes=card_types_without_subtypes,
    )

    return {
        "metadata": {
            "rules_version": effective_date.isoformat(),
            "rules_effective_date": effective_date.isoformat(),
            "source_file": source_file,
        },
        "card_types": card_types,
        "supertypes": supertypes,
        "card_types_without_subtypes": card_types_without_subtypes,
        "subtype_categories": subtype_categories,
    }


def _extract_effective_date(rules_text: str) -> date:
    """Extract the effective date from the document header."""
    match = re.search(
        r"These rules are effective as of "
        r"([A-Z][a-z]+ \d{1,2}, \d{4})\.",
        rules_text,
    )

    if match is None:
        raise TaxonomyGenerationError(
            "Could not find the rules effective date in the document."
        )

    try:
        return datetime.strptime(
            match.group(1),
            "%B %d, %Y",
        ).date()
    except ValueError as error:
        raise TaxonomyGenerationError(
            f"Invalid effective date: {match.group(1)}."
        ) from error


def _extract_rule(rules_text: str, rule_id: str) -> str:
    """Return the text of a specific rule."""
    pattern = re.compile(
        rf"^{re.escape(rule_id)}\s+(.+)$",
        re.MULTILINE,
    )

    matches = pattern.findall(rules_text)

    if len(matches) != 1:
        raise TaxonomyGenerationError(
            f"Expected exactly one occurrence of rule {rule_id}, "
            f"found {len(matches)}."
        )

    return matches[0].strip()



def _extract_after_phrase(
    rule_text: str,
    phrase: str,
    rule_id: str,
) -> str:
    """Extract the first sentence following a known phrase."""
    position = rule_text.find(phrase)

    if position < 0:
        raise TaxonomyGenerationError(
            f"Could not find expected text in rule {rule_id}: "
            f"'{phrase.strip()}'."
        )

    result = rule_text[position + len(phrase):].strip()

    # Ignore periods inside rule references such as "301.5".
    sentence_end = re.search(
        r"\.(?=\s+[A-Z“])|\.$",
        result,
    )

    if sentence_end is None:
        raise TaxonomyGenerationError(
            f"Could not find the end of the enumeration in rule {rule_id}."
        )

    return result[:sentence_end.start()].strip()



def _parse_enumeration(value: str, context: str) -> list[str]:
    """Parse a comma-separated enumeration with a final 'and'."""
    value = re.sub(
        r"\s+\(see rule [^)]+\)",
        "",
        value,
        flags=re.IGNORECASE,
    )

    value = re.sub(r",\s+and\s+", ", ", value)
    value = re.sub(r"\s+and\s+", ", ", value)

    items = [item.strip() for item in value.split(",")]

    if not items or any(not item for item in items):
        raise TaxonomyGenerationError(
            f"Invalid enumeration in {context}."
        )

    return items


def _canonicalize_initial(value: str) -> str:
    """Capitalize the first character without changing the rest."""
    return value[0].upper() + value[1:]


def _extract_card_types(rules_text: str) -> list[str]:
    """Extract card types from rule 205.2a."""
    rule_id = "205.2a"
    rule_text = _extract_rule(rules_text, rule_id)

    values = _extract_after_phrase(
        rule_text,
        "The card types are ",
        rule_id,
    )

    return [
        _canonicalize_initial(value)
        for value in _parse_enumeration(values, rule_id)
    ]


def _extract_supertypes(rules_text: str) -> list[str]:
    """Extract supertypes from rule 205.4a."""
    rule_id = "205.4a"
    rule_text = _extract_rule(rules_text, rule_id)

    values = _extract_after_phrase(
        rule_text,
        "The supertypes are ",
        rule_id,
    )

    return [
        _canonicalize_initial(value)
        for value in _parse_enumeration(values, rule_id)
    ]


def _extract_creature_subtypes(rule_text: str) -> list[str]:
    """Extract the complete creature subtype list, including Time Lord."""
    two_word_match = re.search(
        r"One creature type is two words long:\s*(.+?)\.",
        rule_text,
    )

    if two_word_match is None:
        raise TaxonomyGenerationError(
            "Could not find the two-word creature subtype in rule 205.3m."
        )

    two_word_subtype = two_word_match.group(1).strip()

    if not two_word_subtype:
        raise TaxonomyGenerationError(
            "The two-word creature subtype is empty."
        )

    one_word_values = _extract_after_phrase(
        rule_text,
        "All other creature types are one word long: ",
        "205.3m",
    )

    return [two_word_subtype] + _parse_enumeration(
        one_word_values,
        "205.3m",
    )


def _extract_subtype_categories(
    rules_text: str,
) -> dict[str, dict[str, Any]]:
    """Extract all subtype categories and their associated card types."""
    categories: dict[str, dict[str, Any]] = {}

    for category_name, definition in CATEGORY_DEFINITIONS.items():
        rule_id = definition["rule"]
        rule_text = _extract_rule(rules_text, rule_id)

        if category_name == "creature":
            subtypes = _extract_creature_subtypes(rule_text)
        else:
            values = _extract_after_phrase(
                rule_text,
                definition["phrase"],
                rule_id,
            )
            subtypes = _parse_enumeration(values, rule_id)

        categories[category_name] = {
            "card_types": definition["card_types"],
            "values": subtypes,
        }

    return categories


def _extract_card_types_without_subtypes(
    rules_text: str,
) -> list[str]:
    """Extract card types explicitly defined as having no subtypes."""
    rule_id = "205.3r"
    rule_text = _extract_rule(rules_text, rule_id)

    match = re.fullmatch(
        r"(.+?) have no subtypes\.",
        rule_text,
    )

    if match is None:
        raise TaxonomyGenerationError(
            f"Unexpected format in rule {rule_id}."
        )

    descriptions = _parse_enumeration(match.group(1), rule_id)
    card_types = []

    for description in descriptions:
        suffix = " cards"

        if not description.endswith(suffix):
            raise TaxonomyGenerationError(
                f"Unexpected card type description in {rule_id}: "
                f"'{description}'."
            )

        card_types.append(
            _canonicalize_initial(description[:-len(suffix)])
        )

    return card_types


def _validate_taxonomy(
    *,
    card_types: list[str],
    supertypes: list[str],
    subtype_categories: dict[str, dict[str, Any]],
    card_types_without_subtypes: list[str],
) -> None:
    """Validate taxonomy completeness and internal consistency."""
    _validate_unique_values(card_types, "card types")
    _validate_unique_values(supertypes, "supertypes")
    _validate_unique_values(
        card_types_without_subtypes,
        "card types without subtypes",
    )

    expected_categories = set(CATEGORY_DEFINITIONS)
    actual_categories = set(subtype_categories)

    if actual_categories != expected_categories:
        raise TaxonomyGenerationError(
            "Invalid subtype categories. "
            f"Missing: {sorted(expected_categories - actual_categories)}; "
            f"unexpected: {sorted(actual_categories - expected_categories)}."
        )

    known_card_types = {value.casefold() for value in card_types}
    categorized_card_types: set[str] = set()

    for category_name, definition in subtype_categories.items():
        category_card_types = definition["card_types"]
        subtypes = definition["values"]

        _validate_unique_values(
            subtypes,
            f"subtypes in category '{category_name}'",
        )

        for card_type in category_card_types:
            normalized = card_type.casefold()

            if normalized not in known_card_types:
                raise TaxonomyGenerationError(
                    f"Unknown card type '{card_type}' in category "
                    f"'{category_name}'."
                )

            categorized_card_types.add(normalized)

    no_subtype_types = {
        value.casefold()
        for value in card_types_without_subtypes
    }

    unknown_types = no_subtype_types - known_card_types

    if unknown_types:
        raise TaxonomyGenerationError(
            "Unknown card types declared without subtypes: "
            f"{sorted(unknown_types)}."
        )

    overlap = categorized_card_types & no_subtype_types

    if overlap:
        raise TaxonomyGenerationError(
            "Card types cannot both have subtype categories and be "
            f"declared without subtypes: {sorted(overlap)}."
        )

    uncovered_types = (
        known_card_types - categorized_card_types - no_subtype_types
    )

    if uncovered_types:
        raise TaxonomyGenerationError(
            "Card types not covered by any subtype category or the "
            f"no-subtype declaration: {sorted(uncovered_types)}."
        )

    _validate_ambiguous_subtypes(subtype_categories)


def _validate_unique_values(
    values: list[str],
    context: str,
) -> None:
    """Ensure that a list contains no empty or duplicate values."""
    if not values:
        raise TaxonomyGenerationError(
            f"No values found for {context}."
        )

    if any(not value.strip() for value in values):
        raise TaxonomyGenerationError(
            f"Empty value found in {context}."
        )

    normalized = [value.casefold() for value in values]

    if len(normalized) != len(set(normalized)):
        raise TaxonomyGenerationError(
            f"Duplicate values found in {context}."
        )


def _validate_ambiguous_subtypes(
    categories: dict[str, dict[str, Any]],
) -> None:
    """Ensure known cross-category subtype overlaps are preserved."""
    subtype_categories: dict[str, set[str]] = {}

    for category_name, definition in categories.items():
        for subtype in definition["values"]:
            key = subtype.casefold()
            subtype_categories.setdefault(key, set()).add(category_name)

    expected = {"artifact", "planar"}
    actual = subtype_categories.get("spacecraft", set())

    if actual != expected:
        raise TaxonomyGenerationError(
            "The subtype 'Spacecraft' must belong to both the "
            "artifact and planar categories."
        )


def _write_json(
    taxonomy: dict[str, Any],
    output_path: Path,
) -> None:
    """Write deterministic JSON atomically."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            suffix=".tmp",
            prefix=f".{output_path.name}.",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)

            json.dump(
                taxonomy,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )
            temporary_file.write("\n")

        temporary_path.replace(output_path)

    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> int:
    """Run the taxonomy generation command."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate the MTG taxonomy JSON from the "
            "Magic: The Gathering Comprehensive Rules."
        )
    )

    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Path to the Comprehensive Rules text file.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination path for the generated taxonomy JSON.",
    )

    args = parser.parse_args()

    try:
        output_path = generate_taxonomy(
            source_path=args.source,
            output_path=args.output,
        )
    except (OSError, TaxonomyGenerationError) as error:
        print(
            f"Taxonomy generation failed: {error}",
            file=sys.stderr,
        )
        return 1

    print(f"Taxonomy generated successfully: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
