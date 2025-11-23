from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    import networkx as nx


class LoggingMode(str, Enum):
    """Supported logging verbosity for the routing pipeline."""

    NONE = "none"
    INFO = "info"
    DEBUG = "debug"

    @classmethod
    def from_value(cls, value: LoggingMode | str | None) -> LoggingMode:
        """Normalize arbitrary user input into a `LoggingMode`."""
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.NONE
        try:
            return cls(value.lower())
        except ValueError as exc:
            valid = ", ".join(mode.value for mode in cls)
            msg = f"Invalid logging mode: {value!r}. Expected one of {{{valid}}}."
            raise ValueError(msg) from exc


@dataclass(slots=True)
class Logger:
    """Minimal logger that emits deterministic plan-phase updates."""

    mode: LoggingMode = LoggingMode.NONE

    @property
    def is_info_enabled(self) -> bool:  # noqa: D102
        return self.mode in (LoggingMode.INFO, LoggingMode.DEBUG)

    @property
    def is_debug_enabled(self) -> bool:  # noqa: D102
        return self.mode is LoggingMode.DEBUG

    def info(self, message: str, **context: Any) -> None:  # noqa: ANN401, D102
        if self.is_info_enabled:
            self._emit("INFO", message, context)

    def debug(self, message: str, **context: Any) -> None:  # noqa: ANN401, D102
        if self.is_debug_enabled:
            self._emit("DEBUG", message, context)

    def graph_stats(self, graph: nx.MultiGraph) -> None:  # type: ignore[name-defined]
        """Log immediately available stats about the loaded graph."""
        if not self.is_info_enabled:
            return
        stats: dict[str, Any] = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        }
        graph_name = graph.graph.get("name")
        if graph_name:
            stats["name"] = graph_name
        self.info("graph.stats", **stats)

    @contextmanager
    def phase(self, name: str, **details: Any) -> Iterator[None]:  # noqa: ANN401
        """Emit deterministic start/done messages for a logical phase."""
        if not self.is_info_enabled:
            yield
            return

        self.info(f"{name}.start", **details)
        start = perf_counter()
        try:
            yield
        except Exception as exc:
            self.info(f"{name}.failed", error=str(exc))
            raise
        else:
            self.info(f"{name}.complete", **details)
            if self.is_debug_enabled:
                elapsed = perf_counter() - start
                self.debug(f"{name}.elapsed", seconds=f"{elapsed:.3f}")

    def _emit(self, level: str, message: str, context: dict[str, Any]) -> None:
        parts = [f"[{level}]\t{message}"]
        extras = "\t".join(
            f"{key}={value}" for key, value in context.items() if value is not None
        )
        if extras:
            parts.append(extras)
        print("\t".join(parts))
