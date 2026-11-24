import logging
from dataclasses import dataclass
from typing import Sequence

from mtg_variability.extraction.models import Expansion
from mtg_variability.extraction.models import ExtractionResult
from mtg_variability.extraction.protocols import (
    CardDataProvider,
    ExtractionRepository,
)
from mtg_variability.utils.timer import Timer


logger = logging.getLogger(__name__)


class DownloadPipeline:
    """Orchestrates the extraction and persistence of MTG data."""

    def __init__(
        self,
        provider: CardDataProvider,
        repository: ExtractionRepository,
    ):
        self.provider = provider
        self.repository = repository

    def run(self) -> ExtractionResult:
        logger.info("Starting MTG data extraction")

        with Timer(
            message="Total extraction time",
            logger=logger.info,
        ):
            expansions = self.provider.get_expansions()

            self.repository.save_expansions(expansions)

            failed: list[str] = []
            downloaded = 0
            skipped = 0

            for index, expansion in enumerate(expansions, start=1):
                logger.info(
                    "(%d/%d) Processing %s [%s]",
                    index,
                    len(expansions),
                    expansion.name,
                    expansion.code,
                )

                if self.repository.has_expansion(expansion, index):
                    logger.info("Already downloaded, skipping")
                    skipped += 1
                    continue

                try:
                    with Timer(
                        message=f"Downloading {expansion.code}",
                        logger=logger.info,
                    ):
                        cards = self.provider.get_cards(expansion.code)
                        self.repository.save_cards(expansion, cards, index)

                    downloaded += 1

                    logger.info(
                        "Saved %d cards for %s",
                        len(cards),
                        expansion.code,
                    )

                except Exception:
                    logger.exception(
                        "Failed to download expansion %s",
                        expansion.code,
                    )
                    failed.append(expansion.code)

        return ExtractionResult(
            total_expansions=len(expansions),
            downloaded=downloaded,
            skipped=skipped,
            failed=failed,
        )