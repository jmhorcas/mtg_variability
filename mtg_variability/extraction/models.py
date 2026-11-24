from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True, slots=True)
class Expansion:
    """Represents a Magic: The Gathering expansion."""

    code: str
    name: str
    release_date: str | None = None


@dataclass(frozen=True, slots=True)
class Card:
    """Represents a Magic: The Gathering card."""

    id: str | None
    multiverse_id: int | None
    number: str | None

    # Provider-independent representation of card attributes.
    attributes: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Summary of an extraction execution."""

    total_expansions: int
    downloaded: int
    skipped: int
    failed: list[str]

    @property
    def successful(self) -> bool:
        return not self.failed