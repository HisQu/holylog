"""Required dependency validation helpers for Holylog logging."""

from __future__ import annotations

from importlib import import_module
from typing import Any

STRUCTLOG_INSTALL_HINT = (
    "Holylog requires structlog>=25.5. Install or repair Holylog runtime "
    'dependencies with: python -m pip install "holylog"'
)
STRUCTLOG_COMPATIBILITY_HINT = (
    "Holylog requires structlog>=25.5 with contextvars, stdlib, and processors "
    'support. Install compatible dependencies with: python -m pip install "holylog"'
)


def _is_missing_structlog(exc: ModuleNotFoundError) -> bool:
    """Return whether an import failure is for structlog itself.

    :param exc: Module import failure raised while loading structlog.
    :return: ``True`` when the dependency is missing.
    """

    name = exc.name or ""
    return name == "structlog" or name.startswith("structlog.")


def _is_missing_structlog_package(exc: ModuleNotFoundError) -> bool:
    """Return whether the root structlog package is absent.

    :param exc: Module import failure raised while loading structlog.
    :return: ``True`` when Python could not import the root package.
    """

    return exc.name == "structlog"


def missing_structlog_error() -> ImportError:
    """Return the public error used when required structlog support is absent.

    :return: Import error with the Holylog installation hint.
    """

    return ImportError(STRUCTLOG_INSTALL_HINT)


def incompatible_structlog_error(detail: str) -> ImportError:
    """Return the public error for unsupported structlog installations.

    :param detail: Short description of the missing API surface.
    :return: Import error with Holylog's structlog compatibility guidance.
    """

    return ImportError(f"{STRUCTLOG_COMPATIBILITY_HINT} Missing: {detail}.")


def _require_module(module_name: str) -> Any:
    """Import one required structlog module or raise compatibility guidance.

    :param module_name: Fully qualified structlog module path.
    :return: Imported module.
    :raises ImportError: If the installed structlog package is incompatible.
    """

    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        if _is_missing_structlog_package(exc):
            raise missing_structlog_error() from exc
        raise incompatible_structlog_error(module_name) from exc


def _require_attr(owner: Any, dotted_name: str) -> None:
    """Validate one required attribute path on a module-like object.

    :param owner: Module or object owning the first path segment.
    :param dotted_name: Dot-separated attribute path that must exist.
    :raises ImportError: If the installed structlog package is incompatible.
    """

    value = owner
    for part in dotted_name.split("."):
        try:
            value = getattr(value, part)
        except AttributeError as exc:
            raise incompatible_structlog_error(dotted_name) from exc


def require_structlog_contextvars() -> Any:
    """Return required structlog contextvars support.

    :return: Imported ``structlog.contextvars`` module.
    :raises ImportError: If structlog is missing or lacks contextvars support.
    """

    contextvars = _require_module("structlog.contextvars")
    _require_attr(contextvars, "bind_contextvars")
    _require_attr(contextvars, "reset_contextvars")
    _require_attr(contextvars, "unbind_contextvars")
    return contextvars


def validate_structlog() -> Any:
    """Return a validated structlog module or raise Holylog guidance.

    :return: Imported ``structlog`` module.
    :raises ImportError: If structlog is missing or incompatible.
    """

    try:
        structlog = import_module("structlog")
    except ModuleNotFoundError as exc:
        if not _is_missing_structlog(exc):
            raise
        raise missing_structlog_error() from exc
    contextvars = require_structlog_contextvars()
    stdlib = _require_module("structlog.stdlib")
    processors = _require_module("structlog.processors")
    _require_attr(contextvars, "merge_contextvars")
    _require_attr(stdlib, "ProcessorFormatter")
    _require_attr(stdlib, "ExtraAdder")
    _require_attr(processors, "EventRenamer")
    _require_attr(processors, "JSONRenderer")
    return structlog


__all__ = [
    "STRUCTLOG_COMPATIBILITY_HINT",
    "STRUCTLOG_INSTALL_HINT",
    "incompatible_structlog_error",
    "missing_structlog_error",
    "require_structlog_contextvars",
    "validate_structlog",
]
