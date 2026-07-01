from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
import sys
import threading
import textwrap
from pathlib import Path
from typing import Any

import pytest
import structlog.contextvars as structlog_contextvars

from holylog.logging.context import CID
import holylog as hlog

ROOT = Path(__file__).resolve().parents[1]


def _json_log_lines(output: str) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in output.splitlines() if line.startswith("{")
    ]


def _raise_with_logging_locals(
    harmless_value: str,
    token_secret: str,
) -> None:
    safe_value = harmless_value
    api_key = token_secret
    if not safe_value or not api_key:
        raise AssertionError("test helper needs values")
    raise RuntimeError("boom")


def _exception_local_names(exception: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for stack in exception:
        for frame in stack.get("frames", []):
            locals_ = frame.get("locals", {})
            if isinstance(locals_, dict):
                names.update(str(key) for key in locals_)
        for nested in stack.get("exceptions", []):
            names.update(_exception_local_names(nested))
    return names


def _exception_local_values(exception: list[dict[str, Any]]) -> str:
    values: list[str] = []
    for stack in exception:
        for frame in stack.get("frames", []):
            locals_ = frame.get("locals", {})
            if isinstance(locals_, dict):
                values.extend(str(value) for value in locals_.values())
        for nested in stack.get("exceptions", []):
            values.append(_exception_local_values(nested))
    return "\n".join(values)


def _holylog_handlers(logger: logging.Logger) -> list[logging.Handler]:
    return [
        handler
        for handler in logger.handlers
        if getattr(handler, "_holylog_handler", False) is True
    ]


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def _structlog_cid() -> object | None:
    return structlog_contextvars.get_contextvars().get("cid")


def test_flat_import_exports_public_api() -> None:
    assert hlog.get_logger is not None
    assert hlog.setup_logging is not None
    assert hlog.AppLogger is not None
    assert hlog.DependencyHandlerPolicy is not None
    assert hlog.cid_context is not None
    assert hlog.REDACTED_VALUE == "[redacted]"
    assert hlog.SEMANTIC_EVENTS["SUCCESS"].name == "SUCCESS"
    assert "setup_logger" not in hlog.__all__
    assert not hasattr(hlog, "setup_logger")


def test_get_logger_infers_caller_module() -> None:
    log = hlog.get_logger()

    assert isinstance(log, hlog.AppLogger)
    assert log.name == __name__


def test_get_logger_returns_named_stdlib_logger_subclass() -> None:
    log = hlog.get_logger("holylog.tests.normal_contract")

    assert isinstance(log, logging.Logger)
    assert isinstance(log, hlog.AppLogger)
    assert log is logging.getLogger("holylog.tests.normal_contract")


def test_get_logger_rejects_precreated_plain_logger() -> None:
    script = textwrap.dedent(
        """
        import logging

        plain_logger = logging.getLogger("holylog.tests.precreated_plain")
        assert type(plain_logger) is logging.Logger

        import holylog as hlog

        try:
            hlog.get_logger("holylog.tests.precreated_plain")
        except RuntimeError as exc:
            assert "install_app_logger_class()" in str(exc)
            assert "get_logger()" in str(exc)
        else:
            raise AssertionError("pre-created plain logger was accepted")
        """
    )
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            (str(ROOT / "src"), os.environ.get("PYTHONPATH", ""))
        ),
    }
    subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def test_setup_logging_can_configure_named_logger_without_replacing_root() -> (
    None
):
    root = logging.getLogger()
    sentinel = logging.NullHandler()
    target = logging.getLogger("holylog.tests.named_logger")
    root.addHandler(sentinel)
    try:
        hlog.setup_logging(
            level="DEBUG",
            colorize=False,
            force=True,
            logger="holylog.tests.named_logger",
        )

        assert sentinel in root.handlers
        assert target.handlers
        assert target.level == logging.DEBUG
        assert target.propagate is False
    finally:
        _clear_handlers(target)
        target.propagate = True
        root.removeHandler(sentinel)


def test_setup_logging_preserves_host_handlers_without_force() -> None:
    target = logging.getLogger("holylog.tests.handler_preserve")
    _clear_handlers(target)
    target.propagate = True
    sentinel = logging.NullHandler()
    target.addHandler(sentinel)
    try:
        hlog.setup_logging(
            level="INFO",
            colorize=False,
            force=False,
            logger=target,
        )

        holylog_handlers = _holylog_handlers(target)
        assert sentinel in target.handlers
        assert len(holylog_handlers) == 1
        assert target.level == logging.INFO
        assert target.propagate is False
    finally:
        _clear_handlers(target)
        target.propagate = True


def test_setup_logging_updates_holylog_handler_without_duplicates() -> None:
    target = logging.getLogger("holylog.tests.handler_update")
    _clear_handlers(target)
    try:
        hlog.setup_logging(
            level="INFO",
            renderer="mini",
            colorize=False,
            force=False,
            logger=target,
        )
        handler = _holylog_handlers(target)[0]
        first_formatter = handler.formatter

        hlog.setup_logging(
            level="DEBUG",
            renderer="json",
            colorize=False,
            force=False,
            logger=target,
        )

        holylog_handlers = _holylog_handlers(target)
        assert holylog_handlers == [handler]
        assert handler.formatter is not first_formatter
        assert target.level == logging.DEBUG
    finally:
        _clear_handlers(target)
        target.propagate = True


def test_setup_logging_force_replaces_target_handlers() -> None:
    target = logging.getLogger("holylog.tests.handler_force")
    _clear_handlers(target)
    target.propagate = True
    sentinel = logging.NullHandler()
    target.addHandler(sentinel)
    try:
        hlog.setup_logging(
            level="WARNING",
            colorize=False,
            force=True,
            logger=target,
        )

        holylog_handlers = _holylog_handlers(target)
        assert sentinel not in target.handlers
        assert target.handlers == holylog_handlers
        assert len(holylog_handlers) == 1
        assert target.level == logging.WARNING
        assert target.propagate is False
    finally:
        _clear_handlers(target)
        target.propagate = True


def test_dependency_logger_policy_preserves_handlers_by_default() -> None:
    target = logging.getLogger("holylog.tests.dependency_target")
    dependency = logging.getLogger("holylog.tests.dependency_preserve")
    _clear_handlers(target)
    _clear_handlers(dependency)
    dependency.propagate = False
    sentinel = logging.NullHandler()
    dependency.addHandler(sentinel)
    try:
        hlog.setup_logging(
            level="INFO",
            colorize=False,
            force=True,
            logger=target,
            dependency_levels={dependency.name: logging.ERROR},
        )

        assert dependency.level == logging.ERROR
        assert dependency.handlers == [sentinel]
        assert dependency.propagate is False
    finally:
        _clear_handlers(target)
        _clear_handlers(dependency)
        target.propagate = True
        dependency.propagate = True


def test_dependency_logger_policy_can_clear_handlers() -> None:
    target = logging.getLogger("holylog.tests.dependency_clear_target")
    dependency = logging.getLogger("holylog.tests.dependency_clear")
    _clear_handlers(target)
    _clear_handlers(dependency)
    dependency.propagate = False
    sentinel = logging.NullHandler()
    dependency.addHandler(sentinel)
    try:
        hlog.setup_logging(
            level="INFO",
            colorize=False,
            force=True,
            logger=target,
            dependency_levels={dependency.name: logging.WARNING},
            dependency_handler_policy="clear",
        )

        assert dependency.level == logging.WARNING
        assert dependency.handlers == []
        assert dependency.propagate is True
    finally:
        _clear_handlers(target)
        _clear_handlers(dependency)
        target.propagate = True
        dependency.propagate = True


def test_semantic_logger_preserves_structured_fields_and_validation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log = hlog.get_logger("holylog.tests.semantic")

    with caplog.at_level(logging.INFO, logger="holylog.tests.semantic"):
        log.success("done", extra_struct={"rows": 2})

    record = caplog.records[-1]
    assert record.getMessage() == "done"
    assert record.event_type == "SUCCESS"
    assert record.rows == 2

    with caplog.at_level(logging.INFO, logger="holylog.tests.semantic"):
        with pytest.raises(TypeError, match="extra_struct"):
            log.info("bad", rows=1)
        with pytest.raises(
            KeyError,
            match="Duplicate logging structured field",
        ):
            log.info("bad", extra={"rows": 1}, extra_struct={"rows": 2})


@pytest.mark.parametrize(
    ("method_name", "message", "level", "icon", "expected"),
    [
        ("trace", "trace message", logging.DEBUG, "🐛", "trace message"),
        ("debug", "debug message", logging.DEBUG, "🐞", "debug message"),
        ("action_begin", "start", logging.INFO, "⚛️", "start ..."),
        ("action_success", "done", logging.INFO, "☑️", "done"),
        ("info_begin", "begin", logging.INFO, "▶️ ", "begin"),
        ("info", "info message", logging.INFO, "📃", "info message"),
        ("wait", "waiting", logging.INFO, "💤", "waiting ..."),
        ("save", "saved", logging.INFO, "💾", "saved"),
        ("telemetry", "metrics", logging.INFO, "👀", "metrics"),
        ("success", "success", logging.INFO, "✅", "success"),
        ("warning", "warning", logging.WARNING, "⚠️", "warning"),
        ("retry", "retry", logging.WARNING, "🔄", "retry ..."),
        ("fallback", "fallback", logging.WARNING, "🚑", "fallback ..."),
        ("error", "error", logging.ERROR, "❌", "error"),
        ("critical", "critical", logging.CRITICAL, "💀", "critical"),
    ],
)
def test_semantic_helpers_preserve_metadata(
    caplog: pytest.LogCaptureFixture,
    method_name: str,
    message: str,
    level: int,
    icon: str,
    expected: str,
) -> None:
    hlog.setup_logging(level="DEBUG", colorize=False, force=False)
    log = hlog.get_logger("holylog.tests.helpers")

    with caplog.at_level(logging.DEBUG, logger="holylog.tests.helpers"):
        getattr(log, method_name)(message)

    record = caplog.records[-1]
    assert record.levelno == level
    assert record.getMessage() == expected
    assert record.icon == icon
    assert record.event_type


def test_semantic_events_include_usage_documentation() -> None:
    assert all(event.documentation for event in hlog.SEMANTIC_EVENTS.values())
    assert (
        hlog.SEMANTIC_EVENTS["TRACE"].documentation == "Step-by-step debugging"
    )
    assert (
        hlog.SEMANTIC_EVENTS["SUCCESS"].documentation
        == "Finish the whole script"
    )


def test_cid_helpers_propagate_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hlog.setup_logging(level="INFO", colorize=False, force=False)
    log = hlog.get_logger("holylog.tests.cid")
    cid = hlog.set_cid(hlog.new_cid())

    with caplog.at_level(logging.INFO, logger="holylog.tests.cid"):
        log.info("with cid")

    assert caplog.records[-1].cid == cid
    hlog.clear_cid()
    assert CID.get() is None


def test_cid_context_creates_and_restores_empty_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hlog.clear_cid()
    structlog_contextvars.clear_contextvars()
    hlog.setup_logging(level="INFO", colorize=False, force=False)
    log = hlog.get_logger("holylog.tests.cid_context_empty")

    try:
        with hlog.cid_context() as cid:
            assert cid
            assert CID.get() == cid
            assert _structlog_cid() == cid
            with caplog.at_level(
                logging.INFO,
                logger="holylog.tests.cid_context_empty",
            ):
                log.info("with generated cid")

        assert caplog.records[-1].cid == cid
        assert CID.get() is None
        assert _structlog_cid() is None
    finally:
        hlog.clear_cid()
        structlog_contextvars.clear_contextvars()


def test_cid_context_restores_outer_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hlog.clear_cid()
    structlog_contextvars.clear_contextvars()
    hlog.setup_logging(level="INFO", colorize=False, force=False)
    log = hlog.get_logger("holylog.tests.cid_context_nested")
    outer = hlog.set_cid("outer-cid")

    try:
        with caplog.at_level(
            logging.INFO,
            logger="holylog.tests.cid_context_nested",
        ):
            with hlog.cid_context("inner-cid") as inner:
                log.info("inner")
                assert inner == "inner-cid"
                assert CID.get() == "inner-cid"
                assert _structlog_cid() == "inner-cid"
            log.info("outer")

        assert outer == "outer-cid"
        assert CID.get() == "outer-cid"
        assert _structlog_cid() == "outer-cid"
        assert caplog.records[-2].cid == "inner-cid"
        assert caplog.records[-1].cid == "outer-cid"
    finally:
        hlog.clear_cid()
        structlog_contextvars.clear_contextvars()


@pytest.mark.asyncio
async def test_async_cid_context_restores_outer_scope() -> None:
    hlog.clear_cid()
    structlog_contextvars.clear_contextvars()
    outer = hlog.set_cid("outer-async")

    try:
        async with hlog.cid_context("async-cid") as cid:
            await asyncio.sleep(0)
            assert cid == "async-cid"
            assert CID.get() == "async-cid"
            assert _structlog_cid() == "async-cid"

        assert outer == "outer-async"
        assert CID.get() == "outer-async"
        assert _structlog_cid() == "outer-async"
    finally:
        hlog.clear_cid()
        structlog_contextvars.clear_contextvars()


def test_json_logging_includes_extras_and_structured_exceptions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    hlog.setup_logging(
        level="DEBUG",
        renderer="json",
        colorize=False,
        force=True,
        exception_show_locals=True,
    )
    log = hlog.get_logger("holylog.tests.json_exceptions")
    harmless = "-".join(("visible", "safe", "local"))
    benchmark_secret = "-".join(("private", "api", "value"))

    try:
        _raise_with_logging_locals(harmless, benchmark_secret)
    except RuntimeError as exc:
        log.traceback(
            "json failed",
            exc=exc,
            extra_struct={
                "answer": 42,
                "OPENAI_KEY": benchmark_secret,
            },
        )

    payload = _json_log_lines(capsys.readouterr().err)[-1]
    assert payload["message"] == "json failed:"
    assert payload["logger"] == "holylog.tests.json_exceptions"
    assert payload["answer"] == 42
    assert payload["OPENAI_KEY"] == hlog.REDACTED_VALUE
    assert payload["event_type"] == "TRACEBACK"

    exception = payload["exception"]
    local_names = _exception_local_names(exception)
    local_values = _exception_local_values(exception)
    assert any(stack["exc_type"] == "RuntimeError" for stack in exception)
    assert "safe_value" in local_names
    assert harmless in local_values
    assert "api_key" not in local_names
    assert benchmark_secret not in local_values


@pytest.mark.asyncio
async def test_async_logs_include_task_names(
    capsys: pytest.CaptureFixture[str],
) -> None:
    hlog.setup_logging(level="INFO", colorize=False, force=True)
    log = hlog.get_logger("holylog.tests.async")

    async def worker(tag: str) -> None:
        log.info(f"hello {tag}")

    await asyncio.gather(
        asyncio.create_task(worker("A"), name="TaskA"),
        asyncio.create_task(worker("B"), name="TaskB"),
    )

    stderr = capsys.readouterr().err
    assert "TaskA" in stderr
    assert "TaskB" in stderr
    assert "hello A" in stderr
    assert "hello B" in stderr


def test_thread_logs_include_thread_names(
    capsys: pytest.CaptureFixture[str],
) -> None:
    hlog.setup_logging(level="INFO", colorize=False, force=True)
    log = hlog.get_logger("holylog.tests.threads")

    def worker(tag: str) -> None:
        log.info(f"thread {tag}")

    thread = threading.Thread(target=worker, args=("X",), name="Thread-X")
    thread.start()
    thread.join()

    stderr = capsys.readouterr().err
    assert "Thread-X" in stderr
    assert "thread X" in stderr


def test_lifecycle_decorator_logs_initialization(
    caplog: pytest.LogCaptureFixture,
) -> None:
    @hlog.log_init_lifecycle(label="Class", log_done=True)
    class Example:
        def __init__(self) -> None:
            self.ready = True

    with caplog.at_level(logging.INFO, logger=__name__):
        item = Example()

    assert item.ready is True
    messages = [record.getMessage() for record in caplog.records]
    assert any("⚙️🔜 INITIALIZING: Class 'Example' ..." in m for m in messages)
    assert any("⚙️✔️  Class 'Example' initialized!" in m for m in messages)


def test_forward_cli_output_logs_streams(
    caplog: pytest.LogCaptureFixture,
) -> None:
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr)",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    log = hlog.get_logger("holylog.tests.forward")

    with caplog.at_level(logging.INFO, logger="holylog.tests.forward"):
        return_code = hlog.forward_cli_output(process, logger=log)

    assert return_code == 0
    assert "out" in caplog.text
    assert "err" in caplog.text
