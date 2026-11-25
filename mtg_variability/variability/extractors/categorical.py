
"""Extractor for simple categorical card attributes."""

from collections import defaultdict
from collections.abc import Sequence

from mtg_variability.variability.extractors.base import BaseVariationExtractor
from mtg_variability.variability.models import (
    VariabilityCategory,
    VariationPointSpec,
    VariantSpec,
)
from mtg_variability.variability.protocols import CardRecord


class CategoricalExtractor(BaseVariationExtractor):
    """Discover variability in a single categorical card attribute.

    Each distinct non-missing attribute value becomes a variant.
    Attributes with fewer than two distinct values do not produce
    a variation point unless some observations are missing.

    The extractor is intentionally domain-independent. It does not
    interpret MTG-specific structures or multi-valued attributes.
    """

    def __init__(
        self,
        attribute: str,
        *,
        example_attribute: str = "name",
        max_examples: int = 3,
        category: VariabilityCategory | str = VariabilityCategory.FUNCTIONAL,
    ) -> None:
        """Initialize the categorical extractor.

        Args:
            attribute: Dataset attribute to analyze.
            example_attribute: Attribute used to obtain example card names.
            max_examples: Maximum number of examples stored per variant.
            category: Semantic category assigned to the variation point.

        Raises:
            ValueError: If an attribute name is empty, max_examples
                is not a positive integer, or the category is invalid.
        """
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
        return f"categorical:{self._attribute}"

    def _extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        """Extract a variation point from the configured attribute."""
        occurrences: dict[str, int] = defaultdict(int)
        examples: dict[str, list[str]] = defaultdict(list)

        missing_count = 0

        for record in records:
            raw_value = self._get_value(record, self._attribute)

            if self._is_missing(raw_value):
                missing_count += 1
                continue

            value = self._normalize_value(raw_value)
            value = " ".join(value.split())

            if not value:
                missing_count += 1
                continue

            occurrences[value] += 1

            example = self._get_normalized_value(
                record,
                self._example_attribute,
            )

            if (
                example
                and example not in examples[value]
                and len(examples[value]) < self._max_examples
            ):
                examples[value].append(example)

        # A constant attribute is relevant when some records lack it.
        if not occurrences or (
            len(occurrences) == 1 and missing_count == 0
        ):
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
