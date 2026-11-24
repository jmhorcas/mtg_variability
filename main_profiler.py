from pathlib import Path

from mtg_variability.variability.persistence.csv_reader import (
    CSVCardDatasetReader,
)
from mtg_variability.variability.discovery.profiler import (
    DatasetProfiler,
)

records = CSVCardDatasetReader().read(Path("data/cards/0001-LEA-Limited Edition Alpha.csv"))

profile = DatasetProfiler().profile(records)

print(f"Cards: {profile.total_records}")
print(f"Attributes: {profile.attribute_count}")

for name, attribute in profile.attributes.items():
    print(f"\n{name}")
    print(f"  Distinct values: {attribute.distinct_count}")
    print(f"  Missing: {attribute.missing_count}")
    print(f"  Missing ratio: {attribute.missing_ratio:.2%}")
    print(f"  Most common: {attribute.most_common(5)}")