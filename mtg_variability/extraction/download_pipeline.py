import csv
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence, TextIO

import mtgsdk

from .api_client import DownloadError, with_retries
from .transformers import (
    ALL_CARD_PROPERTIES,
    EXPANSION_PROPERTIES,
    extract_expansion_info,
    extract_product_features_from_card,
    is_base_number,
)


logger = logging.getLogger("mtg_download")


class DownloadPipeline:
    """Phase 1: Download expansion and cards from mtgsdk and persist them in CSVs."""

    def __init__(self, data_dir: Path = Path("data")):
        self.products_dir = data_dir / "products"
        self.expansions_file = data_dir / "expansions" / "all_expansions.csv"
        self.products_dir.mkdir(parents=True, exist_ok=True)
        self.expansions_file.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _atomic_writer(self, path: Path, newline: str | None = None) -> Iterator[TextIO]:
        tmp_path = path.with_name(path.name + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8", newline=newline) as file:
                yield file
            tmp_path.replace(path)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _write_csv(self, path: Path, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
        with self._atomic_writer(path, newline="") as file:
            writer = csv.writer(file, delimiter=",")
            writer.writerow(header)
            writer.writerows(rows)

    def _fetch_unique_cards(self, set_code: str) -> list[mtgsdk.Card]:
        raw_cards = with_retries(
            lambda: mtgsdk.Card.where(set=set_code, language="English").all(),
            description=f"[{set_code}] card download",
        )
        unique: dict[Any, mtgsdk.Card] = {}
        for card in raw_cards:
            if card.multiverse_id is not None:
                unique.setdefault(("mv", card.multiverse_id), card)
            elif is_base_number(card.number):
                unique.setdefault(("id", card.id), card)
        return list(unique.values())

    def run(self) -> list[str]:
        logger.info("🚀 Phase 1: Starting download from mtgsdk")
        all_expansions = with_retries(mtgsdk.Set.all, description="Expansion list download")
        all_expansions.sort(key=lambda s: s.release_date or "")
        total = len(all_expansions)

        # Save general expansion catalog
        exp_rows = [
            [extract_expansion_info(s)[field] for field in EXPANSION_PROPERTIES]
            for s in all_expansions
        ]
        self._write_csv(self.expansions_file, EXPANSION_PROPERTIES, exp_rows)

        failed: list[str] = []
        for i, set_exp in enumerate(all_expansions, start=1):
            safe_name = set_exp.name.split("/")[-1].replace(":", "_")
            csv_path = self.products_dir / f"{i:04d}-{set_exp.code}-{safe_name}.csv"

            if csv_path.exists():
                logger.info("⏭️ (%d/%d) %s already downloaded, skipping", i, total, set_exp.name)
                continue

            logger.info("📥 (%d/%d) Downloading %s [%s]...", i, total, set_exp.name, set_exp.code)
            try:
                cards = self._fetch_unique_cards(set_exp.code)
                rows = [
                    [extract_product_features_from_card(c)[field] for field in ALL_CARD_PROPERTIES]
                    for c in cards
                ]
                self._write_csv(csv_path, ALL_CARD_PROPERTIES, rows)
                logger.info("✅ (%d/%d) %s saved (%d cards)", i, total, set_exp.name, len(cards))
            except DownloadError as exc:
                logger.error("❌ Error downloading %s: %s", set_exp.code, exc)
                failed.append(set_exp.code)

        return failed