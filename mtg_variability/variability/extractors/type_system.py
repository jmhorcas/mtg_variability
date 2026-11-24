
"""Extractor for Magic: The Gathering card type systems."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
import re

from mtg_variability.variability.extractors.base import BaseVariationExtractor
from mtg_variability.variability.models import VariationPointSpec, VariantSpec
from mtg_variability.variability.protocols import CardRecord
from mtg_variability.variability.taxonomy import MTGTaxonomy, SubtypeCategory


@dataclass(frozen=True, slots=True)
class ParsedTypeLine:
    """Represent the semantic components of a parsed type line."""

    supertypes: frozenset[str]
    card_types: frozenset[str]
    subtypes: tuple[tuple[SubtypeCategory, str], ...]
    unknown_prefix_values: tuple[str, ...] = ()
    unknown_subtypes: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        """Return whether the type line contains no recognized values."""
        return not (
            self.supertypes
            or self.card_types
            or self.subtypes
            or self.unknown_prefix_values
            or self.unknown_subtypes
        )


class TypeLineParser:
    """Parse MTG type lines using a loaded taxonomy.

    The parser recognizes supertypes, card types and subtypes.
    Subtype matching is case-insensitive and uses the longest
    matching taxonomy entry first.
    """

    _TYPE_LINE_SEPARATOR = re.compile(r"\s+[—–]\s+")

    def __init__(self, taxonomy: MTGTaxonomy) -> None:
        self._taxonomy = taxonomy

        self._supertypes = {
            value.casefold(): value
            for value in taxonomy.supertypes
        }

        self._card_types = {
            value.casefold(): value
            for value in taxonomy.card_types
        }

        self._subtypes_by_category = {
            category: {
                value.casefold(): value
                for value in taxonomy.get_subtypes(category)
            }
            for category in SubtypeCategory
        }

    def parse(self, type_line: str) -> ParsedTypeLine:
        """Parse one type line, including multi-face type lines."""
        if not isinstance(type_line, str):
            raise TypeError("Type line must be a string.")

        if not type_line.strip():
            return ParsedTypeLine(
                supertypes=frozenset(),
                card_types=frozenset(),
                subtypes=(),
            )

        faces = [
            face.strip()
            for face in type_line.split("//")
            if face.strip()
        ]

        supertypes: set[str] = set()
        card_types: set[str] = set()
        subtypes: set[tuple[SubtypeCategory, str]] = set()
        unknown_prefix_values: set[str] = set()
        unknown_subtypes: set[str] = set()

        for face in faces:
            parsed = self._parse_face(face)

            supertypes.update(parsed.supertypes)
            card_types.update(parsed.card_types)
            subtypes.update(parsed.subtypes)
            unknown_prefix_values.update(parsed.unknown_prefix_values)
            unknown_subtypes.update(parsed.unknown_subtypes)

        return ParsedTypeLine(
            supertypes=frozenset(supertypes),
            card_types=frozenset(card_types),
            subtypes=tuple(
                sorted(
                    subtypes,
                    key=lambda item: (
                        item[0].value,
                        item[1].casefold(),
                        item[1],
                    ),
                )
            ),
            unknown_prefix_values=tuple(
                sorted(unknown_prefix_values, key=str.casefold)
            ),
            unknown_subtypes=tuple(
                sorted(unknown_subtypes, key=str.casefold)
            ),
        )

    def _parse_face(self, face: str) -> ParsedTypeLine:
        """Parse one face of a potentially multi-face card."""
        parts = self._TYPE_LINE_SEPARATOR.split(face, maxsplit=1)

        prefix = parts[0].strip()
        subtype_text = parts[1].strip() if len(parts) == 2 else ""

        parsed_supertypes: set[str] = set()
        parsed_card_types: set[str] = set()
        unknown_prefix_values: set[str] = set()

        for token in prefix.split():
            normalized = token.casefold()

            if normalized in self._supertypes:
                parsed_supertypes.add(self._supertypes[normalized])
            elif normalized in self._card_types:
                parsed_card_types.add(self._card_types[normalized])
            else:
                unknown_prefix_values.add(token)

        parsed_subtypes, unknown_subtypes = self._parse_subtypes(
            subtype_text,
            parsed_card_types,
        )

        return ParsedTypeLine(
            supertypes=frozenset(parsed_supertypes),
            card_types=frozenset(parsed_card_types),
            subtypes=tuple(parsed_subtypes),
            unknown_prefix_values=tuple(unknown_prefix_values),
            unknown_subtypes=tuple(unknown_subtypes),
        )

    def _parse_subtypes(
        self,
        subtype_text: str,
        card_types: set[str],
    ) -> tuple[
        list[tuple[SubtypeCategory, str]],
        list[str],
    ]:
        """Match subtype names against categories applicable to card types."""
        if not subtype_text:
            return [], []

        applicable_categories = {
            category
            for card_type in card_types
            for category in self._taxonomy.get_categories_for_card_type(
                card_type
            )
        }

        if not applicable_categories:
            return [], subtype_text.split()

        candidates: list[tuple[str, SubtypeCategory, str]] = []

        for category in applicable_categories:
            for normalized, canonical in self._subtypes_by_category[
                category
            ].items():
                candidates.append(
                    (normalized, category, canonical)
                )

        # Prefer the longest matching subtype to support multi-word names.
        candidates.sort(
            key=lambda item: (-len(item[0].split()), item[0], item[1].value)
        )

        tokens = subtype_text.split()
        matched: list[tuple[SubtypeCategory, str]] = []
        unknown: list[str] = []

        position = 0

        while position < len(tokens):
            match = self._find_subtype_match(tokens, position, candidates)

            if match is None:
                unknown.append(tokens[position])
                position += 1
                continue

            token_count, category, canonical = match
            matched.append((category, canonical))
            position += token_count

        return matched, unknown

    @staticmethod
    def _find_subtype_match(
        tokens: list[str],
        position: int,
        candidates: list[tuple[str, SubtypeCategory, str]],
    ) -> tuple[int, SubtypeCategory, str] | None:
        """Find the longest subtype match starting at a token position."""
        for normalized, category, canonical in candidates:
            parts = normalized.split()
            end = position + len(parts)

            if end > len(tokens):
                continue

            candidate = " ".join(tokens[position:end]).casefold()

            if candidate == normalized:
                return len(parts), category, canonical

        return None


class TypeSystemExtractor(BaseVariationExtractor):
    """Discover variability in MTG supertypes, card types and subtypes."""

    def __init__(
        self,
        taxonomy: MTGTaxonomy,
        *,
        attribute: str = "type",
        example_attribute: str = "name",
        max_examples: int = 3,
    ) -> None:
        """Initialize the type system extractor.

        Args:
            taxonomy: Loaded MTG taxonomy.
            attribute: Dataset attribute containing the type line.
            example_attribute: Attribute used to obtain example card names.
            max_examples: Maximum number of examples per variant.

        Raises:
            ValueError: If an attribute name is empty or max_examples
                is not a positive integer.
        """
        normalized_attribute = attribute.strip()
        normalized_example_attribute = example_attribute.strip()

        if not normalized_attribute:
            raise ValueError("Attribute name cannot be empty.")

        if not normalized_example_attribute:
            raise ValueError("Example attribute cannot be empty.")

        if (
            isinstance(max_examples, bool)
            or not isinstance(max_examples, int)
            or max_examples < 1
        ):
            raise ValueError("max_examples must be a positive integer.")

        self._taxonomy = taxonomy
        self._attribute = normalized_attribute
        self._example_attribute = normalized_example_attribute
        self._max_examples = max_examples
        self._parser = TypeLineParser(taxonomy)

    @property
    def name(self) -> str:
        """Return the unique registry name of this extractor."""
        return f"type-system:{self._attribute}"

    def _extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        """Extract the hierarchical type system specification."""
        counts: dict[str, dict[str, int]] = {
            "supertypes": defaultdict(int),
            "card_types": defaultdict(int),
        }

        examples: dict[str, dict[str, list[str]]] = {
            "supertypes": defaultdict(list),
            "card_types": defaultdict(list),
        }

        subtype_counts: dict[SubtypeCategory, dict[str, int]] = {
            category: defaultdict(int)
            for category in SubtypeCategory
        }

        subtype_examples: dict[
            SubtypeCategory,
            dict[str, list[str]],
        ] = {
            category: defaultdict(list)
            for category in SubtypeCategory
        }

        category_observations: dict[SubtypeCategory, int] = defaultdict(int)
        category_missing: dict[SubtypeCategory, int] = defaultdict(int)

        unknown_prefix_counts: dict[str, int] = defaultdict(int)
        unknown_subtype_counts: dict[str, int] = defaultdict(int)

        missing_count = 0

        for record in records:
            raw_type_line = self._get_value(record, self._attribute)

            if self._is_missing(raw_type_line):
                missing_count += 1
                continue

            parsed = self._parser.parse(raw_type_line)

            if parsed.is_empty:
                missing_count += 1
                continue

            example = self._get_normalized_value(
                record,
                self._example_attribute,
            )

            self._accumulate_values(
                "supertypes",
                parsed.supertypes,
                counts,
                examples,
                example,
            )

            self._accumulate_values(
                "card_types",
                parsed.card_types,
                counts,
                examples,
                example,
            )

            subtypes_by_category: dict[
                SubtypeCategory,
                set[str],
            ] = defaultdict(set)

            for category, value in parsed.subtypes:
                subtypes_by_category[category].add(value)

            for card_type in parsed.card_types:
                for category in self._taxonomy.get_categories_for_card_type(
                    card_type
                ):
                    category_observations[category] += 1

                    if not subtypes_by_category[category]:
                        category_missing[category] += 1

            for category, values in subtypes_by_category.items():
                for value in values:
                    subtype_counts[category][value] += 1

                    self._append_example(
                        subtype_examples[category][value],
                        example,
                    )

            for value in parsed.unknown_prefix_values:
                unknown_prefix_counts[value] += 1

            for value in parsed.unknown_subtypes:
                unknown_subtype_counts[value] += 1

        supertype_point = self._build_point(
            name="supertypes",
            source_attribute=self._attribute,
            counts=counts["supertypes"],
            examples=examples["supertypes"],
            total_observations=len(records),
            missing_observations=missing_count,
        )

        card_type_point = self._build_point(
            name="card_types",
            source_attribute=self._attribute,
            counts=counts["card_types"],
            examples=examples["card_types"],
            total_observations=len(records),
            missing_observations=missing_count,
        )

        subtype_points = tuple(
            point
            for category in SubtypeCategory
            if (
                point := self._build_point(
                    name=f"subtypes:{category.value}",
                    source_attribute=self._attribute,
                    counts=subtype_counts[category],
                    examples=subtype_examples[category],
                    total_observations=category_observations[category],
                    missing_observations=category_missing[category],
                )
            ) is not None
        )

        subtype_root = (
            VariationPointSpec(
                name="subtypes",
                source_attributes=(self._attribute,),
                child_points=subtype_points,
                total_observations=len(records),
                missing_observations=missing_count,
            )
            if subtype_points
            else None
        )

        children = tuple(
            point
            for point in (
                supertype_point,
                card_type_point,
                subtype_root,
            )
            if point is not None
        )

        if not children:
            return ()

        metadata = {}

        if unknown_prefix_counts:
            metadata["unknown_prefix_values"] = dict(
                sorted(unknown_prefix_counts.items())
            )

        if unknown_subtype_counts:
            metadata["unknown_subtypes"] = dict(
                sorted(unknown_subtype_counts.items())
            )

        return (
            VariationPointSpec(
                name="type",
                source_attributes=(self._attribute,),
                child_points=children,
                total_observations=len(records),
                missing_observations=missing_count,
                metadata=metadata,
            ),
        )

    def _accumulate_values(
        self,
        group: str,
        values: Sequence[str] | frozenset[str],
        counts: dict[str, dict[str, int]],
        examples: dict[str, dict[str, list[str]]],
        example: str,
    ) -> None:
        """Accumulate distinct values once per card."""
        for value in values:
            counts[group][value] += 1
            self._append_example(examples[group][value], example)

    def _append_example(
        self,
        values: list[str],
        example: str,
    ) -> None:
        """Append a distinct example while respecting the configured limit."""
        if (
            example
            and example not in values
            and len(values) < self._max_examples
        ):
            values.append(example)

    def _build_point(
        self,
        *,
        name: str,
        source_attribute: str,
        counts: dict[str, int],
        examples: dict[str, list[str]],
        total_observations: int,
        missing_observations: int,
    ) -> VariationPointSpec | None:
        """Build a variation point from accumulated values."""
        if not counts:
            return None

        variants = tuple(
            VariantSpec(
                name=value,
                occurrences=counts[value],
                examples=tuple(examples[value]),
            )
            for value in sorted(
                counts,
                key=lambda item: (item.casefold(), item),
            )
        )

        return VariationPointSpec(
            name=name,
            source_attributes=(source_attribute,),
            variants=variants,
            total_observations=total_observations,
            missing_observations=missing_observations,
        )
