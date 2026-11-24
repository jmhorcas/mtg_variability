
"""Extractor for attributes containing multiple values."""

import ast
from collections import defaultdict
from collections.abc import Sequence

from mtg_variability.variability.extractors.base import BaseVariationExtractor
from mtg_variability.variability.models import (
    VariabilityCategory,
    VariationPointSpec,
    VariantSpec,
)
from mtg_variability.variability.protocols import CardRecord


class MultiValueExtractor(BaseVariationExtractor):
    """Discover variability in an attribute containing multiple values.

    Each distinct element found in the attribute becomes an independent
    variant. Multiple variants can therefore occur in the same record.

    The source attribute is expected to contain a serialized Python list,
    such as "['W', 'U']".
    """

    def __init__(
        self,
        attribute: str,
        *,
        example_attribute: str = "name",
        max_examples: int = 3,
        category: VariabilityCategory | str = VariabilityCategory.FUNCTIONAL,
    ) -> None:
        """Initialize the multi-value extractor."""
        normalized_attribute = attribute.strip()

        if not normalized_attribute:
            raise ValueError("Attribute name cannot be empty.")

        normalized_example_attribute = example_attribute.strip()

        if not normalized_example_attribute:
            raise ValueError("Example attribute cannot be empty.")

        if (
            isinstance(max_examples, bool)
            or not isinstance(max_examples, int)
            or max_examples < 1
        ):
            raise ValueError("max_examples must be a positive integer.")

        try:
            normalized_category = VariabilityCategory(category)
        except (ValueError, TypeError) as error:
            allowed_categories = ", ".join(
                item.value for item in VariabilityCategory
            )
            raise ValueError(
                f"Invalid variability category: {category!r}. "
                f"Expected one of: {allowed_categories}."
            ) from error

        self._attribute = normalized_attribute
        self._example_attribute = normalized_example_attribute
        self._max_examples = max_examples
        self._category = normalized_category

    @property
    def name(self) -> str:
        """Return the unique registry name of this extractor."""
        return f"multi-value:{self._attribute}"

    def _parse_values(self, raw_value: str) -> tuple[str, ...]:
        """Parse a serialized list and normalize its elements."""
        try:
            parsed = ast.literal_eval(raw_value)
        except (SyntaxError, ValueError) as error:
            raise ValueError(
                f"Invalid serialized list in attribute "
                f"'{self._attribute}': {raw_value!r}."
            ) from error

        if not isinstance(parsed, list):
            raise ValueError(
                f"Expected a list in attribute '{self._attribute}', "
                f"got {type(parsed).__name__}."
            )

        values: list[str] = []

        for item in parsed:
            if not isinstance(item, str):
                raise ValueError(
                    f"Expected string elements in attribute "
                    f"'{self._attribute}', got {type(item).__name__}."
                )

            value = " ".join(item.strip().split())

            if value and value not in values:
                values.append(value)

        return tuple(values)

    def _extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        """Extract independent variants from a multi-value attribute."""
        occurrences: dict[str, int] = defaultdict(int)
        examples: dict[str, list[str]] = defaultdict(list)

        missing_count = 0

        for record in records:
            raw_value = self._get_value(record, self._attribute)

            if self._is_missing(raw_value):
                missing_count += 1
                continue

            values = self._parse_values(raw_value)

            example = self._get_normalized_value(
                record,
                self._example_attribute,
            )

            for value in values:
                occurrences[value] += 1

                if (
                    example
                    and example not in examples[value]
                    and len(examples[value]) < self._max_examples
                ):
                    examples[value].append(example)

        # A constant or entirely empty attribute is not a variation point.
        if len(occurrences) < 2:
            return ()

        variants = tuple(
            VariantSpec(
                name=value,
                occurrences=occurrences[value],
                examples=tuple(examples[value]),
            )
            for value in sorted(
                occurrences,
                key=lambda item: (item.casefold(), item),
            )
        )

        return (
            VariationPointSpec(
                name=self._attribute,
                source_attributes=(self._attribute,),
                variants=variants,
                total_observations=len(records),
                missing_observations=missing_count,
                category=self._category,
            ),
        )
