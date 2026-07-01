"""Runtime context helpers and processors for Holylog logging.

This module owns values that are true at emission or formatting time rather
than values chosen by the caller. ``CID`` stores an optional correlation ID in a
``ContextVar`` so async tasks can carry request/batch identity without passing
it through every function. ``current_task_name`` records the active asyncio task
or OS thread for console scans.

The structured logging processors here are deliberately conservative: they use
``setdefault`` so explicit caller fields survive, and they copy stdlib
``LogRecord`` attributes into renderer-friendly names only when a record is
available. The module itself stays stdlib-only so semantic loggers can still
emit before formatting is configured.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from contextvars import ContextVar, Token
from datetime import datetime
from time import perf_counter
from types import TracebackType
from typing import Any

from holylog.logging._optional import optional_structlog_contextvars


CID: ContextVar[str | None] = ContextVar("holylog_cid", default=None)
STARTED_AT = datetime.now().astimezone()
STARTED_MONOTONIC = perf_counter()


def _bind_cid(
    value: str | None = None,
) -> tuple[str, Token[str | None], Any | None, dict[str, Any] | None]:
    """Bind a CID and return tokens needed for scoped restoration.

    :param value: Explicit correlation ID, or ``None`` to create a new one.
    :return: Active CID, Holylog token, structlog contextvars module, and
        structlog token mapping.
    """

    cid = value or new_cid()
    cid_token = CID.set(cid)
    structlog_contextvars = optional_structlog_contextvars()
    structlog_tokens = None
    if structlog_contextvars is not None:
        structlog_tokens = dict(structlog_contextvars.bind_contextvars(cid=cid))
    return cid, cid_token, structlog_contextvars, structlog_tokens


class _CidContext:
    """Context manager that restores the previous CID on exit.

    :param value: Explicit correlation ID, or ``None`` to create a new one.
    """

    def __init__(self, value: str | None = None) -> None:
        self._value = value
        self._cid_token: Token[str | None] | None = None
        self._structlog_contextvars: Any | None = None
        self._structlog_tokens: dict[str, Any] | None = None

    def __enter__(self) -> str:
        """Bind the scoped CID.

        :return: Active correlation ID for the scope.
        """

        if self._cid_token is not None:
            raise RuntimeError("cid_context cannot be entered twice at once")
        cid, cid_token, structlog_contextvars, structlog_tokens = _bind_cid(
            self._value
        )
        self._cid_token = cid_token
        self._structlog_contextvars = structlog_contextvars
        self._structlog_tokens = structlog_tokens
        return cid

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Restore CID state when leaving a ``with`` block.

        :param exc_type: Exception type supplied by the context protocol.
        :param exc: Exception instance supplied by the context protocol.
        :param tb: Traceback supplied by the context protocol.
        :return: ``None``.
        """

        self._reset()

    async def __aenter__(self) -> str:
        """Bind the scoped CID for ``async with`` usage.

        :return: Active correlation ID for the scope.
        """

        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Restore CID state when leaving an ``async with`` block.

        :param exc_type: Exception type supplied by the context protocol.
        :param exc: Exception instance supplied by the context protocol.
        :param tb: Traceback supplied by the context protocol.
        :return: ``None``.
        """

        self._reset()

    def _reset(self) -> None:
        """Restore the context-local CID state captured on entry.

        :return: ``None``.
        """

        if self._cid_token is None:
            return
        CID.reset(self._cid_token)
        if (
            self._structlog_contextvars is not None
            and self._structlog_tokens is not None
        ):
            self._structlog_contextvars.reset_contextvars(
                **self._structlog_tokens
            )
        self._cid_token = None
        self._structlog_contextvars = None
        self._structlog_tokens = None


def new_cid() -> str:
    """Create a short random correlation ID.

    :return: Eight-character hexadecimal correlation ID.
    """

    return uuid.uuid4().hex[:8]


def set_cid(value: str | None = None) -> str:
    """Bind a correlation ID to the current context.

    The ID is always stored in Holylog's own ``ContextVar``. Holylog also
    mirrors the value into structlog's contextvars storage so direct structlog
    usage sees the same ``cid`` field.

    :param value: Explicit correlation ID, or ``None`` to create a new one.
    :return: The active correlation ID.
    """

    cid, _, _, _ = _bind_cid(value)
    return cid


def cid_context(value: str | None = None) -> _CidContext:
    """Return a context manager for a scoped correlation ID.

    The manager supports both ``with`` and ``async with``. It yields the active
    CID and restores the previous Holylog and structlog contextvars state when
    the scope exits.

    :param value: Explicit correlation ID, or ``None`` to create a new one.
    :return: Context manager that yields the active correlation ID.
    """

    return _CidContext(value)


def clear_cid() -> None:
    """Remove the current correlation ID from available context stores.

    :return: ``None``.
    """

    CID.set(None)
    structlog_contextvars = optional_structlog_contextvars()
    if structlog_contextvars is not None:
        structlog_contextvars.unbind_contextvars("cid")


def current_task_name() -> str:
    """Return the active asyncio task name or current thread name.

    :return: Human-readable concurrent workload identifier.
    """

    try:
        task = asyncio.current_task()
    except RuntimeError:
        task = None
    if task is not None:
        return task.get_name()
    return threading.current_thread().name


def add_runtime_context(
    logger: object | None,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Add task/thread and correlation fields when missing.

    This processor runs for Holylog records and foreign stdlib records. It fills
    ``task`` with the active asyncio task name when possible and otherwise uses
    the current thread name. ``cid`` is ``"-"`` when no correlation ID was
    bound.

    :param logger: Logger currently processed by the structured formatter.
    :param method_name: Logging method name such as ``info`` or ``warning``.
    :param event_dict: Mutable structured log event.
    :return: The updated event dictionary.
    """

    event_dict.setdefault("task", current_task_name())
    event_dict.setdefault("cid", CID.get() or "-")
    return event_dict


def add_log_record_fields(
    logger: object | None,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Copy stdlib ``LogRecord`` fields into renderer-friendly names.

    Structlog's ``ProcessorFormatter`` stores the original record under
    ``_record``. Holylog copies stable pieces such as logger name, level, source
    line, and timestamp so console and JSON renderers do not need to know the
    stdlib ``LogRecord`` API.

    :param logger: Logger currently processed by the structured formatter.
    :param method_name: Logging method name such as ``info`` or ``warning``.
    :param event_dict: Mutable structured log event.
    :return: The updated event dictionary.
    """

    record = event_dict.get("_record")
    if not isinstance(record, logging.LogRecord):
        return event_dict

    event_dict.setdefault("logger", record.name)
    event_dict.setdefault("level", record.levelname.lower())
    event_dict.setdefault("level_name", record.levelname)
    event_dict.setdefault("level_no", record.levelno)
    event_dict.setdefault("module", record.module)
    event_dict.setdefault("function", record.funcName)
    event_dict.setdefault("line", record.lineno)
    event_dict.setdefault("pathname", record.pathname)
    event_dict.setdefault("created", record.created)

    for key in ("event_type", "icon", "task", "cid", "color"):
        if hasattr(record, key):
            event_dict.setdefault(key, getattr(record, key))
    return event_dict


def elapsed_seconds() -> float:
    """Return seconds elapsed since this logging module was imported.

    The console renderer uses this monotonic clock for a process-relative
    elapsed column that is not affected by wall-clock changes.

    :return: Monotonic elapsed seconds.
    """

    return perf_counter() - STARTED_MONOTONIC


__all__ = [
    "CID",
    "STARTED_AT",
    "add_log_record_fields",
    "add_runtime_context",
    "cid_context",
    "clear_cid",
    "current_task_name",
    "elapsed_seconds",
    "new_cid",
    "set_cid",
]
