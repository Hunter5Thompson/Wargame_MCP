"""Minimal subset of structlog's API for offline environments."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


class _ContextVarsModule:
    @staticmethod
    def merge_contextvars(_logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        return event_dict


class _JSONRenderer:
    def __call__(self, _logger, _method_name: str, event_dict: dict[str, Any]) -> str:
        return json.dumps(event_dict, default=str)


class _TimeStamper:
    def __init__(self, fmt: str = "iso") -> None:
        self.fmt = fmt

    def __call__(self, _logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        if self.fmt == "iso":
            event_dict.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        return event_dict


class _StackInfoRenderer:
    def __call__(self, _logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        return event_dict


def _add_log_level(_logger, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    event_dict.setdefault("level", method_name.upper())
    return event_dict


def _format_exc_info(_logger, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return event_dict


class _ProcessorsModule:
    TimeStamper = _TimeStamper
    StackInfoRenderer = _StackInfoRenderer
    JSONRenderer = _JSONRenderer

    add_log_level = staticmethod(_add_log_level)
    format_exc_info = staticmethod(_format_exc_info)


contextvars = _ContextVarsModule()
processors = _ProcessorsModule()


@dataclass
class _Logger:
    name: str | None = None
    _logger: logging.Logger = field(init=False)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(self.name or "wargame_mcp")

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(json.dumps({"event": event, **kwargs}, default=str))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(json.dumps({"event": event, **kwargs}, default=str))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(json.dumps({"event": event, **kwargs}, default=str))


def configure(**_kwargs: Any) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def get_logger(name: str | None = None) -> _Logger:
    return _Logger(name)

