
"""Registry for variability extractors."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from mtg_variability.variability.protocols import VariationExtractor


class ExtractorRegistry:
    """Registry that manages the available variability extractors.

    Extractors are identified by their unique names. Registration order
    is preserved to ensure deterministic execution.
    """

    def __init__(
        self,
        extractors: Iterable[VariationExtractor] | None = None,
    ) -> None:
        self._extractors: dict[str, VariationExtractor] = {}

        if extractors is not None:
            for extractor in extractors:
                self.register(extractor)

    def register(self, extractor: VariationExtractor) -> None:
        """Registers a variability extractor.

        Args:
            extractor: Extractor to register.

        Raises:
            TypeError: If the object does not implement the extractor
                contract.
            ValueError: If the extractor name is empty or already
                registered.
        """
        if not isinstance(extractor, VariationExtractor):
            raise TypeError(
                "Extractor must implement the VariationExtractor protocol."
            )

        name = extractor.name

        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                "Extractor name must be a non-empty string."
            )

        if name in self._extractors:
            raise ValueError(
                f"An extractor named '{name}' is already registered."
            )

        self._extractors[name] = extractor

    def unregister(self, name: str) -> VariationExtractor:
        """Removes and returns a registered extractor.

        Args:
            name: Unique extractor name.

        Raises:
            KeyError: If no extractor with the given name exists.
        """
        return self._extractors.pop(name)

    def get(self, name: str) -> VariationExtractor:
        """Returns a registered extractor by name.

        Raises:
            KeyError: If no extractor with the given name exists.
        """
        return self._extractors[name]

    def contains(self, name: str) -> bool:
        """Checks whether an extractor is registered."""
        return name in self._extractors

    def clear(self) -> None:
        """Removes all registered extractors."""
        self._extractors.clear()

    @property
    def names(self) -> tuple[str, ...]:
        """Returns registered extractor names in registration order."""
        return tuple(self._extractors)

    @property
    def extractors(self) -> tuple[VariationExtractor, ...]:
        """Returns registered extractors in registration order."""
        return tuple(self._extractors.values())

    def __len__(self) -> int:
        """Returns the number of registered extractors."""
        return len(self._extractors)

    def __iter__(self) -> Iterator[VariationExtractor]:
        """Iterates over registered extractors in registration order."""
        return iter(self.extractors)

    def __contains__(self, name: object) -> bool:
        """Checks whether an extractor name is registered."""
        return name in self._extractors
