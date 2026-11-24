import logging
import time
from typing import Callable, TypeVar


logger = logging.getLogger(__name__)

T = TypeVar("T")


class DownloadError(RuntimeError):
    """Raised when a download operation fails after all retries."""


def with_retries(
    action: Callable[[], T],
    description: str,
    retries: int = 5,
    backoff_base: int = 2,
) -> T:
    """Execute an operation using exponential backoff."""

    if retries < 1:
        raise ValueError("retries must be greater than zero")

    for attempt in range(1, retries + 1):
        try:
            return action()

        except Exception as exc:
            if attempt == retries:
                raise DownloadError(
                    f"{description} failed after {retries} attempts: {exc!r}"
                ) from exc

            wait = backoff_base ** attempt

            logger.warning(
                "%s: attempt %d/%d failed (%r). Retrying in %ds...",
                description,
                attempt,
                retries,
                exc,
                wait,
            )

            time.sleep(wait)

    raise AssertionError("Unreachable code")