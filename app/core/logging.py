from __future__ import annotations

import logging
import sys
from typing import Any


class StructuredLogger:
    """
    Thin wrapper around stdlib logging that enforces structured key=value output.
    Upgrade to structlog or python-json-logger when observability requirements grow.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def _format(self, message: str, **kwargs: Any) -> str:
        if not kwargs:
            return message
        parts = " ".join(f"{k}={v!r}" for k, v in kwargs.items())
        return f"{message} {parts}"

    def debug(self, message: str, **kwargs: Any) -> None:
        self._logger.debug(self._format(message, **kwargs))

    def info(self, message: str, **kwargs: Any) -> None:
        self._logger.info(self._format(message, **kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self._logger.warning(self._format(message, **kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self._logger.error(self._format(message, **kwargs))

    def exception(self, message: str, **kwargs: Any) -> None:
        self._logger.exception(self._format(message, **kwargs))


def configure_logging(level: str = "INFO") -> None:
    """Call once at application startup."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> StructuredLogger:
    """Return a structured logger for the given module name."""
    return StructuredLogger(name)
