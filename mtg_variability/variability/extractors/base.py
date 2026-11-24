
"""Base classes and shared utilities for variability extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import final, Sequence

from mtg_variability.variability.models import VariationPointSpec
from mtg_variability.variability.protocols import CardRecord


class BaseVariationExtractor(ABC):
    """Abstract base class for variability extractors.

    Concrete extractors implement the domain-specific logic required
    to identify variation points in a collection of card records.

    This class provides a common extraction entry point and utilities
    for accessing and normalizing attribute values.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns the extractor's unique name."""
        ...

    @final
    def extract(
        self,
        records: Sequence[CardRecord],
    ) -> tuple[VariationPointSpec, ...]:
        """Extracts variation points from card records.

        Empty datasets produce no variation points.

        Args:
            records: Card records to analyze.

        Returns:
            An immutable sequence of extracted variation points.
        """
        if not records:
            return ()

        return tuple(self._extract(records))

    @abstractmethod
    def _extract(
        self,
        records: Sequence[CardRecord],
    ) -> Sequence[VariationPointSpec]:
        """Implements the extraction logic in a concrete extractor."""
        ...

    @staticmethod
    def _get_value(
        record: CardRecord,
        attribute: str,
    ) -> str:
        """Returns the raw value of an attribute.

        Missing attributes are represented as empty strings.
        The original value is preserved without normalization.
        """
        return record.get(attribute, "")

    @staticmethod
    def _normalize_value(value: str) -> str:
        """Removes leading and trailing whitespace from a value."""
        return value.strip()

    @staticmethod
    def _is_missing(value: str) -> bool:
        """Checks whether a value is empty or contains only whitespace."""
        return not value or not value.strip()

    @classmethod
    def _get_normalized_value(
        cls,
        record: CardRecord,
        attribute: str,
    ) -> str:
        """Returns a normalized attribute value.

        Missing attributes and whitespace-only values produce an
        empty string.
        """
        value = cls._get_value(record, attribute)

        if cls._is_missing(value):
            return ""

        return cls._normalize_value(value)
