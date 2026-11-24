
"""JSON persistence for variability specifications."""

import json
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Final

from mtg_variability.variability.models import VariabilitySpecification


class JSONSpecificationWriter:
    """Persist variability specifications as deterministic JSON files."""

    SCHEMA_VERSION: Final[int] = 1

    def write(
        self,
        specification: VariabilitySpecification,
        path: Path,
    ) -> Path:
        """Write a specification to a JSON file and return its path.

        The output is written atomically: if serialization or writing fails,
        an existing destination file is left untouched.
        """
        if not isinstance(specification, VariabilitySpecification):
            raise TypeError(
                "specification must be a VariabilitySpecification instance."
            )

        destination = Path(path)

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            **asdict(specification),
        }

        destination.parent.mkdir(parents=True, exist_ok=True)

        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)

                json.dump(
                    payload,
                    temporary_file,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                    allow_nan=False,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, destination)

            return destination

        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
