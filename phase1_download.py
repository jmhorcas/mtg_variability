import logging
from pathlib import Path
import sys

from mtg_variability.config import PipelineConfig
from mtg_variability.extraction.adapters.mtgsdk_adapter import MTGSDKAdapter
from mtg_variability.extraction.persistence.csv_repository import CSVRepository
from mtg_variability.extraction.pipeline import DownloadPipeline


logger = logging.getLogger(__name__)


def run_phase1(config: PipelineConfig) -> list[str]:
    """Execute Phase 1: download MTG expansion and card datasets."""

    config.ensure_directories()

    logger.info(
        "=== Phase 1: Downloading cards into %s ===",
        config.products_dir,
    )

    provider = MTGSDKAdapter()
    repository = CSVRepository(products_dir=config.products_dir, expansions_file=config.expansions_file)

    pipeline = DownloadPipeline(provider=provider, repository=repository)

    result = pipeline.run()

    logger.info(
        "Phase 1 summary: %d expansions, %d downloaded, %d skipped, %d failed",
        result.total_expansions,
        result.downloaded,
        result.skipped,
        len(result.failed),
    )

    return result.failed


def main(config_path: Path = Path("config.toml")) -> int:
    config = PipelineConfig.from_toml(config_path)
    config.configure_logging()

    failed = run_phase1(config)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())