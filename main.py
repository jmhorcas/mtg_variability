import sys
import logging
from pathlib import Path

from mtg_variability.extraction.download_pipeline import DownloadPipeline
from mtg_variability.extraction.variant_pipeline import VariantExtractionPipeline
from mtg_variability.uvl_generator.generation_pipeline import UVLGenerationPipeline


logger = logging.getLogger("mtg_variability_pipeline")


def configure_logging() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> int:
    configure_logging()
    data_path = Path("data")
    uvl_output_path = Path("uvl_models/generated")

    # --- FASE 1: Descarga desde mtgsdk (I/O de Red - Opcional si ya tienes los CSVs) ---
    # logger.info("=== Executing Phase 1: Downloading Cards ===")
    # downloader = DownloadPipeline(data_path)
    # failed_sets = downloader.run()
    # if failed_sets:
    #     logger.warning("⚠️ Phase 1 completed with failures in: %s", ", ".join(failed_sets))

    # --- FASE 2: Extracción de Variantes (Offline - Lee CSVs y genera .dat) ---
    # logger.info("\n=== Executing Phase 2: Local Variant Extraction ===")
    # variant_pipeline = VariantExtractionPipeline(data_path)
    # variant_pipeline.run()

    # --- FASE 3: Generación de Modelos UVL (Flamapy - Lee .dat y genera .uvl) ---
    logger.info("\n=== Executing Phase 3: UVL Model Generation ===")
    uvl_pipeline = UVLGenerationPipeline(
        data_dir=data_path, 
        output_dir=uvl_output_path,
        template_path=Path("uvl_models/templates/base.uvl")
    )
    uvl_pipeline.run()

    logger.info("\n🎉 ¡Pipeline finished successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())