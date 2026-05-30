"""BatchStop — propagates hard fail as batch stop signal.

PatchB B-P0-05: Hard fail must propagate as batch stop.
"""
from dataclasses import dataclass, field


@dataclass
class BatchStopSignal:
    """Signal to stop batch processing."""
    reason: str
    source_chapter: str
    source_artifact: str = ""
    error_code: str = ""
    propagate: bool = True


class BatchStopPropagator:
    """Propagates hard fail as batch stop signal."""

    def __init__(self):
        self._stopped = False
        self._stop_signal: BatchStopSignal | None = None
        self._history: list[BatchStopSignal] = []

    def propagate(self, signal: BatchStopSignal) -> None:
        """Propagate a stop signal. All subsequent chapters are blocked."""
        self._stopped = True
        self._stop_signal = signal
        self._history.append(signal)

    def is_stopped(self) -> bool:
        """Check if batch is stopped."""
        return self._stopped

    def get_stop_reason(self) -> str:
        """Get current stop reason."""
        if self._stop_signal:
            return f"[{self._stop_signal.error_code}] {self._stop_signal.reason} (from {self._stop_signal.source_chapter})"
        return ""

    def reset(self) -> None:
        """Reset stop state (for new batch)."""
        self._stopped = False
        self._stop_signal = None

    def get_history(self) -> list[BatchStopSignal]:
        """Get all stop signals."""
        return list(self._history)
