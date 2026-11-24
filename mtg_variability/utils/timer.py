import time
from typing import Any, Callable, Optional
from contextlib import ContextDecorator
from dataclasses import dataclass, field


class TimerError(RuntimeError):
    """Raised when the timer is used incorrectly."""


@dataclass
class Timer(ContextDecorator):
    """Measure elapsed time using a context manager or decorator."""
    
    # Configuration parameters
    message: str = ""
    logger: Callable[[str], None] | None = print
    enabled: bool = True
    
    # Internal attributes (instance only)
    _start_time: int | None = field(default=None, init=False, repr=False)
    _elapsed_time_sec: float = field(default=0.0, init=False, repr=False)

    def start(self) -> None:
        """Start a new timer."""
        if not self.enabled:
            return

        if self._start_time is not None:
            raise TimerError("Timer is already running. Use .stop() to stop it.")

        # Usamos perf_counter_ns para una medición de tiempo de alta resolución para benchmarking
        self._start_time = time.perf_counter_ns()

    def stop(self) -> float:
        """Stop the timer and report the elapsed time."""
        if not self.enabled:
            return 0.0

        if self._start_time is None:
            raise TimerError("Timer is not running. Use .start() to start it.")

        # Calculate the elapsed time
        end_time = time.perf_counter_ns()
        elapsed_ns = end_time - self._start_time
        
        # Store and return the time in seconds (standard unit)
        self._elapsed_time_sec = elapsed_ns * 1e-9
        self._start_time = None

        if self.logger is not None:
            self.logger(self._format_elapsed_time())

        return self._elapsed_time_sec

    def _format_elapsed_time(self) -> str:
        elapsed = self._elapsed_time_sec

        message = f"{self.message} Elapsed time: {elapsed:.4f} s"

        if elapsed >= 3600:
            message += f" ({elapsed / 3600:.2f} h)"
        elif elapsed >= 60:
            message += f" ({elapsed / 60:.2f} m)"

        return message


    # Context Manager Methods
    
    def __enter__(self) -> "Timer":
        """Start a new timer as a context manager."""
        self.start()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        """Stop the timer as a context manager."""
        if self.enabled:
            self.stop()
            
    # Helper method to get the result outside the context
    @property
    def elapsed_time(self) -> float:
        """Return the measured elapsed time."""
        return self._elapsed_time_sec


# Example usage (optional in the file)
if __name__ == '__main__':
    print("Example usage of Timer as a Context Manager:")
    
    with Timer(message="Simple calculation") as t:
        time.sleep(1.234)
    
    print(f"Measured time (from property): {t.elapsed_time:.4f} s")