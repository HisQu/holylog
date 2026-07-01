"""Async telemetry helpers for Holylog's stdlib semantic logger.

Telemetry is a lightweight progress heartbeat for async workflows. The context
manager tags the current async context with a telemetry scope, starts a reporter
task outside that scope, and emits periodic ``TELEMETRY`` log messages through
the normal Holylog logger pipeline. Tasks created inside the scope inherit the
context tag, so snapshots can count them without patching the event loop.

No separate metrics backend is involved. Extra counters are pulled from an
optional callback and included in the human message so they appear in console
logs alongside task/thread counts.
"""

from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import Awaitable, Callable
from contextvars import Context, ContextVar, Token, copy_context
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from holylog.logger import AppLogger, get_logger

_TELEMETRY_SCOPES: ContextVar[tuple[object, ...]] = ContextVar(
    "holylog_telemetry_scopes",
    default=(),
)


def _reporter_context() -> Context:
    """Return a context that keeps caller values except telemetry scopes.

    :return: Context used to run Holylog's internal reporter task.
    """

    context = copy_context()
    context.run(_TELEMETRY_SCOPES.set, ())
    return context


def _frame_name(depth: int = 0) -> str:
    """Return the function name at the requested stack depth.

    :param depth: Additional frames to skip above this helper.
    :return: Function name or ``unknown``.
    """

    frame = inspect.currentframe()
    try:
        for _ in range(depth + 1):
            if frame is None:
                return "unknown"
            frame = frame.f_back
        return frame.f_code.co_name if frame else "unknown"
    finally:
        del frame


class AsyncTelemetryContext:
    """Context manager for periodic async telemetry logging.

    Entering the context captures the current event loop, starts a reporter
    task outside the telemetry scope, and appends this scope to a context
    variable inherited by child tasks. Exiting restores the previous context
    value and signals the reporter to stop. The async exit path awaits the
    reporter so cleanup is deterministic.

    :param interval: Seconds between telemetry messages.
    :param label: Human-readable telemetry scope label.
    :param logger: Logger used for telemetry messages.
    :param include_threads: Whether active OS thread count is reported.
    :param extras: Optional callback returning extra metrics.
    """

    def __init__(
        self,
        *,
        interval: float = 30.0,
        label: str = "",
        logger: AppLogger | None = None,
        include_threads: bool = True,
        extras: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.interval = float(interval)
        self.label = label or _frame_name(depth=1)
        self.logger = logger or get_logger(__name__)
        self.include_threads = include_threads
        self.extras = extras
        self._scope: object = object()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._scope_token: Token[tuple[object, ...]] | None = None
        self._owner_task: asyncio.Task[Any] | None = None
        self._stop_evt: asyncio.Event | None = None
        self._reporter: asyncio.Task[None] | None = None

    def __enter__(self) -> "AsyncTelemetryContext":
        """Start telemetry inside an already-running event loop.

        :return: This context manager.
        """

        self._start()
        return self

    async def __aenter__(self) -> "AsyncTelemetryContext":
        """Start telemetry for ``async with`` usage.

        :return: This context manager.
        """

        self._start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Signal telemetry shutdown from synchronous context-manager exit.

        :param exc_type: Exception type supplied by the context protocol.
        :param exc: Exception instance supplied by the context protocol.
        :param tb: Traceback supplied by the context protocol.
        :return: ``None``.
        """

        self._stop_sync()

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Restore loop state and await reporter shutdown.

        :param exc_type: Exception type supplied by the context protocol.
        :param exc: Exception instance supplied by the context protocol.
        :param tb: Traceback supplied by the context protocol.
        :return: ``None``.
        """

        await self._stop_async()

    def snapshot(self) -> dict[str, Any]:
        """Return the current telemetry counters.

        The snapshot is useful for tests and for callers that want the same
        counters without waiting for the next log interval.

        :return: Snapshot data for active tasks, total tasks, and extras.
        """

        active_scope = len(self._active_scope_tasks())
        tasks_total = len(self._all_tasks())
        data: dict[str, Any] = {
            "label": self.label,
            "active_tasks_in_scope": active_scope,
            "tasks_total": tasks_total,
        }
        if self.include_threads:
            data["threads"] = threading.active_count()
        if self.extras:
            data.update(self.extras())
        return data

    def _start(self) -> None:
        """Bind the telemetry scope and start the reporter task.

        :return: ``None``.
        """

        if self._loop is not None:
            raise RuntimeError("async telemetry context is already active")
        self._loop = asyncio.get_running_loop()
        self._owner_task = asyncio.current_task(self._loop)
        self._stop_evt = asyncio.Event()
        self._reporter = self._loop.create_task(
            self._reporter_loop(),
            name=f"{self.label}:telemetry",
            context=_reporter_context(),
        )
        scopes = _TELEMETRY_SCOPES.get()
        self._scope_token = _TELEMETRY_SCOPES.set((*scopes, self._scope))

    async def _stop_async(self) -> None:
        """Restore telemetry context and await the reporter task.

        :return: ``None``.
        """

        if self._loop is None:
            return
        self._reset_scope()
        if self._stop_evt is not None:
            self._stop_evt.set()
        if self._reporter is not None:
            try:
                await self._reporter
            finally:
                self._reporter = None
        self._loop = None
        self._owner_task = None
        self._stop_evt = None

    def _stop_sync(self) -> None:
        """Restore telemetry context and signal the reporter task.

        :return: ``None``.
        """

        if self._loop is None:
            return
        self._reset_scope()
        if self._stop_evt is not None:
            self._stop_evt.set()

    def _reset_scope(self) -> None:
        """Restore the previous telemetry scope stack.

        :return: ``None``.
        """

        if self._scope_token is None:
            return
        _TELEMETRY_SCOPES.reset(self._scope_token)
        self._scope_token = None

    def _all_tasks(self) -> set[asyncio.Task[Any]]:
        """Return current tasks for the captured loop.

        :return: Tasks for the telemetry loop, or an empty set before start.
        """

        if self._loop is None:
            return set()
        return asyncio.all_tasks(self._loop)

    def _active_scope_tasks(self) -> set[asyncio.Task[Any]]:
        """Return active child tasks that inherited this telemetry scope.

        :return: Active scoped tasks, excluding the owner and reporter tasks.
        """

        return {
            task
            for task in self._all_tasks()
            if not task.done()
            and task is not self._owner_task
            and task is not self._reporter
            and self._task_has_scope(task)
        }

    def _task_has_scope(self, task: asyncio.Task[Any]) -> bool:
        """Return whether ``task`` inherited this telemetry scope.

        :param task: Asyncio task being inspected.
        :return: ``True`` when the task context contains this scope.
        """

        return self._scope in task.get_context().get(_TELEMETRY_SCOPES, ())

    async def _reporter_loop(self) -> None:
        """Emit telemetry until the stop event is set.

        :return: ``None``.
        """

        self.logger.debug(f"Entered reporter loop [{self.label}]")
        await self._emit()
        assert self._stop_evt is not None
        while not self._stop_evt.is_set():
            try:
                await asyncio.wait_for(
                    self._stop_evt.wait(), timeout=self.interval
                )
            except TimeoutError:
                await self._emit()
            else:
                break
        self.logger.debug(f"Exited reporter loop [{self.label}]")

    async def _emit(self, depth: int = 1) -> None:
        """Emit one telemetry message through the configured logger.

        :param depth: Additional stack frames to skip for callsite attribution.
        :return: ``None``.
        """

        snapshot = self.snapshot()
        parts = [
            "[Active / Total Tasks: "
            f"{snapshot['active_tasks_in_scope']}/{snapshot['tasks_total']}]",
        ]
        if "threads" in snapshot:
            parts.append(f"[OS Threads: {snapshot['threads']}]")
        for key, value in snapshot.items():
            if key in {
                "label",
                "active_tasks_in_scope",
                "tasks_total",
                "threads",
            }:
                continue
            parts.append(f"[{key}={value}]")
        self.logger.telemetry(" ".join(parts), depth=depth)


def async_telemetry(
    label: str = "",
    *,
    interval: float = 30.0,
    logger: AppLogger | None = None,
    include_threads: bool = True,
    extras: Callable[[], dict[str, Any]] | None = None,
) -> AsyncTelemetryContext:
    """Create an async telemetry context manager.

    This is the public helper used by ``AppLogger.telemetry_async`` and by
    callers that want to wrap a block directly.

    :param label: Human-readable telemetry scope label.
    :param interval: Seconds between telemetry messages.
    :param logger: Logger used for telemetry messages.
    :param include_threads: Whether active OS thread count is reported.
    :param extras: Optional callback returning extra metrics.
    :return: Async telemetry context manager.
    """

    return AsyncTelemetryContext(
        interval=interval,
        label=label or _frame_name(depth=2),
        logger=logger,
        include_threads=include_threads,
        extras=extras,
    )


P = ParamSpec("P")
R = TypeVar("R")


def with_async_telemetry(
    label: str = "",
    *,
    interval: float = 30.0,
    logger: AppLogger | None = None,
    include_threads: bool = True,
    extras: Callable[[], dict[str, Any]] | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Decorate an async function to run inside telemetry logging.

    The decorated function runs unchanged except that its body is wrapped in an
    ``async_telemetry`` context. Non-async functions are rejected at decoration
    time because the context needs a running event loop.

    :param label: Human-readable telemetry scope label.
    :param interval: Seconds between telemetry messages.
    :param logger: Logger used for telemetry messages.
    :param include_threads: Whether active OS thread count is reported.
    :param extras: Optional callback returning extra metrics.
    :return: Async function decorator.
    """

    def decorate(fn: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(
                "with_async_telemetry can only decorate async functions"
            )

        @wraps(fn)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            telemetry_label = label or getattr(fn, "__qualname__", fn.__name__)
            async with async_telemetry(
                interval=interval,
                label=telemetry_label,
                logger=logger,
                include_threads=include_threads,
                extras=extras,
            ):
                return await fn(*args, **kwargs)

        return wrapped

    return decorate


__all__ = [
    "AsyncTelemetryContext",
    "async_telemetry",
    "with_async_telemetry",
]
