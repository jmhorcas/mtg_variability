from pathlib import Path

from mtg_variability.variability.persistence.csv_reader import (
    CSVCardDatasetReader,
)
from mtg_variability.variability.discovery.profiler import DatasetProfiler
from mtg_variability.variability.discovery.inspector import (
    DatasetInspector,
)

records = CSVCardDatasetReader().read(Path("data/cards/0001-LEA-Limited Edition Alpha.csv"))

profile = DatasetProfiler().profile(records)
inspection = DatasetInspector().inspect(profile)

print(f"Total cards: {inspection.total_records}")
print(f"Total attributes: {inspection.attribute_count}")

print("\nVariability candidates:")

for attribute in inspection.candidates:
    print(
        f"- {attribute.name}: "
        f"{attribute.classification.value} "
        f"({attribute.profile.distinct_count} values)"
    )

print("\nAttributes requiring review:")

for attribute in inspection.attributes_requiring_review:
    print(
        f"- {attribute.name}: "
        f"{attribute.classification.value} — "
        f"{'; '.join(attribute.reasons)}"
    )