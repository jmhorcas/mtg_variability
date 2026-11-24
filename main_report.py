from pathlib import Path

from mtg_variability.variability.persistence.csv_reader import (
    CSVCardDatasetReader,
)
from mtg_variability.variability.discovery.profiler import DatasetProfiler
from mtg_variability.variability.discovery.inspector import DatasetInspector
from mtg_variability.variability.discovery.report import InspectionReport

records = CSVCardDatasetReader().read(Path("data/cards/0001-LEA-Limited Edition Alpha.csv"))

profile = DatasetProfiler().profile(records)
inspection = DatasetInspector().inspect(profile)

report = InspectionReport(max_values=10).render(inspection)

print(report)