from typing import Protocol, Sequence

from mtg_variability.extraction.models import Card, Expansion


class CardDataProvider(Protocol):
    """Port defining the operations required to retrieve MTG data."""

    def get_expansions(self) -> Sequence[Expansion]:
        """Retrieve all available expansions."""
        ...

    def get_expansion(self, set_code: str) -> Expansion | None:
        """Retrieve an expansion by its set code."""
        ...

    def get_cards(self, set_code: str) -> Sequence[Card]:
        """Retrieve all cards belonging to an expansion."""
        ...


class ExtractionRepository(Protocol):
    """Port defining the persistence operations of the extraction process."""

    def save_expansions(self, expansions: Sequence[Expansion]) -> None:
        """Persist the expansion catalog."""
        ...

    def save_cards(
        self,
        expansion: Expansion,
        cards: Sequence[Card],
        index: int
    ) -> None:
        """Persist the cards belonging to an expansion."""

    def has_expansion(self, expansion: Expansion, index: int) -> bool:
        """Check whether an expansion has already been downloaded."""
        ...