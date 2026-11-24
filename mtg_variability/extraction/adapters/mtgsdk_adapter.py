from typing import Any

import mtgsdk

from mtg_variability.extraction.models import Card, Expansion
from mtg_variability.extraction.services.retry import with_retries
from mtg_variability.transformers import ALL_CARD_PROPERTIES, is_base_number


class MTGSDKAdapter:
    """Adapter that translates MTGSDK operations into the application port."""

    def get_expansions(self) -> list[Expansion]:
        raw_expansions = with_retries(
            mtgsdk.Set.all,
            description="Expansion list download",
        )

        expansions = [
            self._to_expansion(expansion)
            for expansion in raw_expansions
        ]

        return sorted(
            expansions,
            key=lambda expansion: expansion.release_date or "",
        )

    def get_expansion(self, set_code: str) -> Expansion | None:
        expansions = self.get_expansions()

        return next(
            (
                expansion
                for expansion in expansions
                if expansion.code.lower() == set_code.lower()
            ),
            None,
        )

    def get_cards(self, set_code: str) -> list[Card]:
        raw_cards = with_retries(
            lambda: mtgsdk.Card.where(
                set=set_code,
                language="English",
            ).all(),
            description=f"[{set_code}] card download",
        )

        unique_cards: dict[tuple[str, Any], Card] = {}

        for raw_card in raw_cards:
            card = self._to_card(raw_card)

            if card.multiverse_id is not None:
                key = ("multiverse", card.multiverse_id)

            elif card.number is not None and is_base_number(card.number):
                key = ("id", card.id)

            else:
                continue

            unique_cards.setdefault(key, card)

        return list(unique_cards.values())

    @staticmethod
    def _to_expansion(raw_expansion: Any) -> Expansion:
        return Expansion(
            code=raw_expansion.code,
            name=raw_expansion.name,
            release_date=raw_expansion.release_date,
        )

    @staticmethod
    def _to_card(raw_card: Any) -> Card:
        """Convert an MTGSDK card into the application representation."""
        attributes = {
            prop: getattr(raw_card, prop, None)
            for prop in ALL_CARD_PROPERTIES
        }

        return Card(
            id=getattr(raw_card, "id", None),
            multiverse_id=getattr(raw_card, "multiverse_id", None),
            number=getattr(raw_card, "number", None),
            attributes=attributes,
        )