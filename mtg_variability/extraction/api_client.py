import socket
import time
import logging
from typing import Callable, TypeVar

import mtgsdk


logger = logging.getLogger("mtg_extract")
T = TypeVar("T")


class DownloadError(RuntimeError):
    """Raised when a download still fails after all retries."""

def with_retries(action: Callable[[], T], description: str, retries: int = 5, backoff_base: int = 2) -> T:
    for attempt in range(1, retries + 1):
        try:
            return action()
        except Exception as exc:
            if attempt == retries:
                raise DownloadError(f"{description} failed after {retries} attempts: {exc!r}") from exc
            wait = backoff_base ** attempt
            logger.warning("⚠️ %s: attempt %d/%d failed (%r). Retrying in %ds...", description, attempt, retries, exc, wait)
            time.sleep(wait)
    raise DownloadError(f"{description}: no attempts were made")