
"""CSV reader for card datasets used in variability analysis."""

from __future__ import annotations

import csv
from pathlib import Path

from mtg_variability.variability.protocols import CardRecord


class CSVCardDatasetReader:
    """Reads card datasets from CSV files.

    Each card is represented as a dictionary mapping CSV column names
    to their corresponding string values.
    """

    def read(self, path: Path) -> list[CardRecord]:
        """Reads all card records from a CSV file.

        Args:
            path: Path to the CSV file.

        Returns:
            A list of card records. Missing cell values are represented
            as empty strings.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            ValueError: If the file has no header, contains invalid
                headers, or has rows with more fields than the header.
        """
        path = Path(path)

        with path.open(
            mode="r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            reader = csv.DictReader(csv_file)

            fieldnames = reader.fieldnames

            if not fieldnames:
                raise ValueError(
                    f"CSV file '{path}' does not contain a header."
                )

            headers = [header.strip() for header in fieldnames]

            if any(not header for header in headers):
                raise ValueError(
                    f"CSV file '{path}' contains an empty column name."
                )

            if len(headers) != len(set(headers)):
                raise ValueError(
                    f"CSV file '{path}' contains duplicate column names."
                )

            reader.fieldnames = headers

            records: list[CardRecord] = []

            for row in reader:
                if None in row:
                    raise ValueError(
                        f"CSV file '{path}' contains more values than "
                        f"columns at line {reader.line_num}."
                    )

                record: CardRecord = {
                    column: value if value is not None else ""
                    for column, value in row.items()
                }

                records.append(record)

        return records
