import csv
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence, TextIO

from mtg_variability.extraction.models import Card, Expansion
from mtg_variability.transformers import (
    ALL_CARD_PROPERTIES,
    EXPANSION_PROPERTIES,
    extract_expansion_info,
    extract_product_features_from_card,
)


class CSVRepository:
    """Repository responsible for persisting extracted data into CSV files."""

    def __init__(self, products_dir: Path, expansions_file: Path) -> None:
        self.products_dir = products_dir
        self.expansions_file = expansions_file

    def save_expansions(self, expansions: Sequence[Expansion]) -> None:
        rows = [
            self._to_row(extract_expansion_info(expansion), EXPANSION_PROPERTIES)
            for expansion in expansions
        ]

        self._write_csv(
            self.expansions_file,
            EXPANSION_PROPERTIES,
            rows,
        )

    def save_cards(self, expansion: Expansion, cards: Sequence[Card], index: int) -> None:
        rows = [
            self._to_row(
                extract_product_features_from_card(card),
                ALL_CARD_PROPERTIES,
            )
            for card in cards
        ]

        self._write_csv(
            self._get_expansion_path(expansion, index),
            ALL_CARD_PROPERTIES,
            rows,
        )

    def has_expansion(self, expansion: Expansion, index: int) -> bool:
        return self._get_expansion_path(expansion, index).exists()

    def _get_expansion_path(self, expansion: Expansion, index: int) -> Path:
        safe_name = (
            expansion.name
            .split("/")[-1]
            .replace(":", "_")
        )

        return self.products_dir / (
            f"{index:04d}-{expansion.code}-{safe_name}.csv"
        )

    @staticmethod
    def _to_row(
        data: dict[str, Any],
        properties: Sequence[str],
    ) -> list[Any]:
        return [data.get(field) for field in properties]

    @staticmethod
    @contextmanager
    def _atomic_writer(
        path: Path,
    ) -> Iterator[TextIO]:
        tmp_path = path.with_name(path.name + ".tmp")

        try:
            with tmp_path.open(
                "w",
                encoding="utf-8",
                newline="",
            ) as file:
                yield file

            tmp_path.replace(path)

        finally:
            tmp_path.unlink(missing_ok=True)

    def _write_csv(
        self,
        path: Path,
        header: Sequence[str],
        rows: Iterable[Sequence[Any]],
    ) -> None:
        with self._atomic_writer(path) as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(rows)