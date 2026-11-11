"""Extract every Magic: The Gathering card ever printed, one CSV per expansion.

Generated files:
    - expansions/all_expansions.csv          : metadata of ALL expansions, one row each
    - variants/<code>-<name>_variants.dat    : distinct values seen per card property (per expansion)
    - products/<code>-<name>.csv             : one row per unique card (per expansion)

The script is resumable: expansions whose products file already exists are skipped,
so after a crash or a Ctrl+C you can simply run it again.
"""
import csv
import json
import logging
import re
import socket
import sys
import time
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple, TextIO, TypeVar

import mtgsdk

logger = logging.getLogger("mtg_extract")

T = TypeVar("T")

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
REQUEST_TIMEOUT_SECONDS = 30   # without this, urllib waits forever on a hung connection
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 2       # waits 2s, 4s, 8s, ... between attempts

MTG_VARIANTS_DIR = Path("variants")
MTG_ALL_VARIANTS_FILE = MTG_VARIANTS_DIR / "all_expansions_variants.dat"
MTG_CARD_COLLECTION_DIR = Path("products")
MTG_EXPANSIONS_FILE = Path("expansions") / "all_expansions.csv"

# Card properties with effect on game play
CARD_PROPERTIES = (
    "mana_cost",
    "cmc",
    "colors",
    "color_identity",
    "type",
    "supertypes",
    "subtypes",
    "rarity",
    "text",
    "number",
    "power",
    "toughness",
    "loyalty",
    "set",
)

ALL_CARD_PROPERTIES = (
    "name",
    "multiverse_id",
    "layout",
    "names",
    "mana_cost",
    "cmc",
    "colors",
    "color_identity",
    "type",
    "supertypes",
    "subtypes",
    "rarity",
    "text",
    "flavor",
    "artist",
    "number",
    "power",
    "toughness",
    "loyalty",
    "variations",
    "watermark",
    "border",
    "timeshifted",
    "hand",
    "life",
    "reserved",
    "release_date",
    "starter",
    "rulings",
    "foreign_names",
    "printings",
    "original_text",
    "original_type",
    "legalities",
    "source",
    "image_url",
    "set",
    "set_name",
    "id",
)

EXPANSION_PROPERTIES = (
    "code",
    "name",
    "gatherer_code",
    "old_code",
    "magic_cards_info_code",
    "release_date",
    "border",
    "type",
    "block",
    "online_only",
    "booster",
    "mkm_id",
    "mkm_name",
)


# --------------------------------------------------------------------------- #
# Infrastructure helpers
# --------------------------------------------------------------------------- #
class DownloadError(RuntimeError):
    """Raised when a download still fails after all retries."""


class OutputPaths(NamedTuple):
    """Output files generated for a single expansion."""
    products: Path
    variants: Path


def _configure_logging(level: int = logging.INFO) -> None:
    """Configure console logging (UTF-8 so emojis work on legacy Windows consoles)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _with_retries(
    action: Callable[[], T],
    description: str,
    retries: int = MAX_RETRIES,
) -> T:
    """Run `action`, retrying with exponential backoff on any error.

    Raises DownloadError once every attempt has failed. KeyboardInterrupt is never swallowed.
    """
    for attempt in range(1, retries + 1):
        try:
            return action()
        except Exception as exc:  # timeout, HTTP 5xx, malformed JSON...
            if attempt == retries:
                raise DownloadError(
                    f"{description} failed after {retries} attempts: {exc!r}"
                ) from exc
            wait = BACKOFF_BASE_SECONDS ** attempt
            logger.warning(
                "⚠️ %s: attempt %d/%d failed (%r). Retrying in %ds...",
                description, attempt, retries, exc, wait,
            )
            time.sleep(wait)
    raise DownloadError(f"{description}: no attempts were made (retries={retries})")


@contextmanager
def _atomic_writer(path: Path, newline: str | None = None) -> Iterator[TextIO]:
    """Write to a temporary file and move it into place only on success.

    This guarantees that an existing output file is always complete, which is what
    the resume logic relies on.
    """
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8", newline=newline) as file:
            yield file
        tmp_path.replace(path)
    finally:
        tmp_path.unlink(missing_ok=True)


def _write_csv(path: Path, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> None:
    with _atomic_writer(path, newline="") as file:
        writer = csv.writer(file, delimiter=",")
        writer.writerow(header)
        writer.writerows(rows)


def _output_paths(set_exp: mtgsdk.Set, index: int) -> OutputPaths:
    """Build the output file paths for an expansion."""
    name = set_exp.name
    if "/" in name:
        name = name.split("/")[-1]
    name = name.replace(":", "_")
    stem = f"{index:04d}-{set_exp.code}-{name}"
    return OutputPaths(
        products=MTG_CARD_COLLECTION_DIR / f"{stem}.csv",
        variants=MTG_VARIANTS_DIR / f"{stem}_variants.dat",
    )


# --------------------------------------------------------------------------- #
# Card / expansion processing
# --------------------------------------------------------------------------- #
def _is_base_number(number: str | None) -> bool:
    """True if the collector number is digits only (no ★, s, p, † ...)."""
    return number is not None and re.fullmatch(r"\d+", number) is not None


def _to_hashable(value: Any) -> Any:
    """Convert a value into something hashable with a stable representation."""
    if isinstance(value, dict):
        # Deterministic serialization (sorted keys)
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    if isinstance(value, (list, tuple, set, frozenset)):
        return json.dumps(sorted(map(str, value)), ensure_ascii=False)
    return value


def extract_variants_from_cards(
    cards: Collection[mtgsdk.Card],
    properties: Sequence[str] = ALL_CARD_PROPERTIES,
) -> dict[str, list[Any]]:
    """Return, for each property, the distinct values found across the given cards."""
    result: dict[str, set[Any]] = {prop: set() for prop in properties}

    for card in cards:
        for prop in properties:
            value = getattr(card, prop, None)
            if value is None:
                continue

            # A collection (list, set...) contributes each element as a variant;
            # a scalar contributes itself.
            if isinstance(value, (list, tuple, set, frozenset)):
                items = value
            else:
                items = [value]

            for item in items:
                result[prop].add(_to_hashable(item))

    # key=str avoids errors when sorting mixed types
    return {prop: sorted(values, key=str) for prop, values in result.items()}


def extract_cards_from_expansion(
    set_exp_code: str,
    retries: int = MAX_RETRIES,
) -> list[mtgsdk.Card]:
    """Download the English cards of an expansion and de-duplicate them.

    Raises DownloadError if the API keeps failing after `retries` attempts.
    """
    cards = _with_retries(
        lambda: mtgsdk.Card.where(set=set_exp_code, language="English").all(),
        description=f"[{set_exp_code}] card download",
        retries=retries,
    )

    unique: dict[Any, mtgsdk.Card] = {}
    for card in cards:
        if card.multiverse_id is not None:
            unique.setdefault(("mv", card.multiverse_id), card)
        elif _is_base_number(card.number):
            unique.setdefault(("id", card.id), card)
    return list(unique.values())


def clean_text(text: Any) -> Any:
    """Make a card's text more legible. Non-string values are returned untouched."""
    if text is None or not isinstance(text, str):
        return text
    # Keep the card's text on a single line
    text = text.replace("\n", "\\n")
    # Remove extra whitespace and tabs
    return " ".join(text.split())


def extract_product_features_from_card(card: mtgsdk.Card) -> dict[str, Any]:
    return {prop: clean_text(getattr(card, prop, None)) for prop in ALL_CARD_PROPERTIES}


def extract_expansion_info(set_exp: mtgsdk.Set) -> dict[str, Any]:
    return {prop: getattr(set_exp, prop, None) for prop in EXPANSION_PROPERTIES}


def _card_row(card: mtgsdk.Card) -> list[Any]:
    features = extract_product_features_from_card(card)
    return [features[field] for field in ALL_CARD_PROPERTIES]


def write_expansions_file(expansions: Iterable[mtgsdk.Set]) -> None:
    """Write the metadata of all expansions into a single CSV (one row per expansion)."""
    rows = []
    for set_exp in expansions:
        info = extract_expansion_info(set_exp)
        rows.append([info[field] for field in EXPANSION_PROPERTIES])
    _write_csv(MTG_EXPANSIONS_FILE, EXPANSION_PROPERTIES, rows)
    logger.info("📝 Expansion info saved: %s (%d rows)", MTG_EXPANSIONS_FILE, len(rows))


def _extract_expansion(set_exp: mtgsdk.Set, paths: OutputPaths) -> int:
    """Download one expansion and write its variants and products files. Returns the card count.

    The products CSV is written last: it is the marker that the expansion is complete.
    """
    # Cards + variants
    cards_list = extract_cards_from_expansion(set_exp.code)
    logger.info("🃏 %s: %d unique cards", set_exp.name, len(cards_list))
    variants = extract_variants_from_cards(cards_list)

    with _atomic_writer(paths.variants) as file:
        for key, values in variants.items():
            file.write(f"{key}: {values}\n")
    logger.debug("💾 Variants saved: %s", paths.variants)

    # Products
    _write_csv(paths.products, ALL_CARD_PROPERTIES, (_card_row(card) for card in cards_list))
    logger.debug("💾 Products saved: %s", paths.products)

    return len(cards_list)


# --------------------------------------------------------------------------- #
# Main flow
# --------------------------------------------------------------------------- #
def extract_products() -> list[str]:
    """Extract all cards from every expansion of all time.

    Generates one .csv file per expansion. Returns the codes of the expansions that failed.
    """
    logger.info("🚀 Starting MTG extraction")

    all_expansions = _with_retries(mtgsdk.Set.all, description="Expansion list download")
    all_expansions.sort(key=lambda s: s.release_date or "")
    total = len(all_expansions)
    logger.info("📚 Expansions found: %d", total)

    for directory in (MTG_EXPANSIONS_FILE.parent, MTG_CARD_COLLECTION_DIR, MTG_VARIANTS_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    # All expansion metadata is already in the list we just downloaded (no extra requests),
    # so the single file is (re)written on every run to keep it up to date.
    write_expansions_file(all_expansions)

    extracted = 0
    skipped = 0
    failed: list[str] = []
    total_cards = 0

    for i, set_exp in enumerate(all_expansions, start=1):
        label = f"({i}/{total}) {set_exp.name} [{set_exp.code}]"
        paths = _output_paths(set_exp, i)

        if paths.products.exists():
            skipped += 1
            logger.info("⏭️ %s already extracted, skipping", label)
            continue

        logger.info("📥 %s downloading...", label)
        try:
            total_cards += _extract_expansion(set_exp, paths)
        except DownloadError as exc:
            # Products file is not written, so the next run will retry this expansion.
            logger.error("❌ %s skipped: %s", label, exc)
            failed.append(set_exp.code)
            continue

        extracted += 1
        logger.info("✅ %s done", label)

    # Accumulator for all expansions variants (disabled)
    # variants_from_all_expansions: dict[str, set[Any]] = {prop: set() for prop in CARD_PROPERTIES}
    # ... inside the loop:
    # for prop in CARD_PROPERTIES:
    #     variants_from_all_expansions[prop].update(variants[prop])
    # ... after the loop:
    # with MTG_ALL_VARIANTS_FILE.open('w', encoding='utf-8') as file:
    #     for prop, values in variants_from_all_expansions.items():
    #         file.write(f'{prop}: {sorted(values, key=str)}\n')

    logger.info(
        "🏁 Finished: %d extracted (%d cards), %d skipped, %d failed",
        extracted, total_cards, skipped, len(failed),
    )
    if failed:
        logger.warning("🔁 Failed expansions (run the script again to retry): %s", ", ".join(failed))
    return failed


def main() -> int:
    _configure_logging()
    socket.setdefaulttimeout(REQUEST_TIMEOUT_SECONDS)
    try:
        failed = extract_products()
    except KeyboardInterrupt:
        logger.warning("🛑 Interrupted by user. Run the script again to resume.")
        return 130
    except DownloadError as exc:
        logger.critical("💥 Could not start extraction: %s", exc)
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
