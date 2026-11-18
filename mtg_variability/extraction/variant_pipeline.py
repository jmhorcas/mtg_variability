import csv
import logging
from pathlib import Path
from typing import Any

from .transformers import (
    ALL_CARD_PROPERTIES,
    CARD_PROPERTIES,
    extract_variants_from_cards,
    parse_csv_row,
)


logger = logging.getLogger("mtg_variants")


class VariantExtractionPipeline:
    """Phase 2: Extracts variant information from local product CSVs and saves them to .dat files."""

    def __init__(self, data_dir: Path = Path("data")):
        self.products_dir = data_dir / "products"
        self.variants_dir = data_dir / "variants"
        self.all_variants_file = self.variants_dir / "all_expansions_variants.dat"
        self.variants_dir.mkdir(parents=True, exist_ok=True)

    def _read_cards_from_csv(self, csv_path: Path) -> list[dict[str, Any]]:
        with csv_path.open("r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            return [parse_csv_row(row) for row in reader]

    def run(self) -> None:
        logger.info("🔍 Phase 2: Extracting variants from local CSVs...")
        csv_files = sorted(self.products_dir.glob("*.csv"))

        global_accumulator: dict[str, set[Any]] = {prop: set() for prop in CARD_PROPERTIES}

        for csv_path in csv_files:
            variant_path = self.variants_dir / f"{csv_path.stem}_variants.dat"
            cards = self._read_cards_from_csv(csv_path)
            variants = extract_variants_from_cards(cards, ALL_CARD_PROPERTIES)

            # Accumulate global variants for the complete universe
            for prop in CARD_PROPERTIES:
                global_accumulator[prop].update(variants[prop])

            # Write variants for this expansion
            with variant_path.open("w", encoding="utf-8") as file:
                for prop, values in variants.items():
                    file.write(f"{prop}: {values}\n")

        # Write consolidated global file
        with self.all_variants_file.open("w", encoding="utf-8") as file:
            for prop, values in global_accumulator.items():
                file.write(f"{prop}: {sorted(values, key=str)}\n")

        logger.info("✅ Phase 2 completed: %d expansions processed and global variants saved.", len(csv_files))