# References

## Table Of Contents

1. [Public API](#public-api)
2. [Setup Logging](#setup-logging)
3. [Renderers](#renderers)
4. [Handler Ownership](#handler-ownership)
5. [Semantic Events](#semantic-events)
6. [Structured Fields](#structured-fields)
7. [Correlation IDs](#correlation-ids)
8. [Telemetry](#telemetry)
9. [Lifecycle Logging](#lifecycle-logging)
10. [Subprocess Output](#subprocess-output)
11. [Redaction](#redaction)
12. [Project Paths](#project-paths)

## Public API

Import Holylog through the flat package facade:

```python
import holylog as hlog
```

| API | Purpose |
|---|---|
| `hlog.get_logger(name=None)` | Return an `AppLogger`; infers caller module when `name` is omitted. |
| `hlog.setup_logging(...)` | Configure stdlib handlers and structlog processors. |
| `hlog.cid_context(value=None)` | Scope a correlation ID and restore the previous value on exit. |
| `hlog.set_cid(value=None)` | Set or create a correlation ID. |
| `hlog.new_cid()` | Create a short random correlation ID. |
| `hlog.clear_cid()` | Clear the active correlation ID. |
| `hlog.AppLogger` | Stdlib logger subclass with semantic helper methods. |
| `hlog.AppConsoleRenderer` | Human-readable renderer used by console modes. |
| `hlog.DependencyHandlerPolicy` | Literal policy: `"preserve"` or `"clear"`. |
| `hlog.LoggingConfig` | Normalized setup dataclass. |
| `hlog.LoggingRenderer` | Literal renderer: `"mini"`, `"cli"`, `"ipy"`, or `"json"`. |
| `hlog.REDACTED_VALUE` | Placeholder used for redacted structured fields and locals. |
| `hlog.SEMANTIC_EVENTS` | Mapping of event names to display metadata. |
| `hlog.SemanticEvent` | Dataclass describing one semantic event. |
| `hlog.install_app_logger_class()` | Install `AppLogger` as the stdlib logger class for future loggers. |
| `hlog.log_init_lifecycle(...)` | Class decorator for initialization breadcrumbs. |
| `hlog.async_telemetry(...)` | Async context manager for periodic telemetry logs. |
| `hlog.with_async_telemetry(...)` | Async function decorator for telemetry logging. |
| `hlog.forward_cli_output(process, logger=...)` | Forward captured subprocess streams into logs. |

## Setup Logging

```python
hlog.setup_logging(
    level="INFO",
    *,
    renderer="mini",
    colorize=True,
    collapse_same_second=True,
    exception_show_locals=True,
    extra_redact_patterns=(),
    dependency_levels=None,
    dependency_handler_policy="preserve",
    force=False,
    logger=None,
)
```

| Parameter | Default | Meaning |
|---|---:|---|
| `level` | `"INFO"` | Level for the target root or named logger. Accepts stdlib level names or numbers. |
| `renderer` | `"mini"` | Output renderer. See [Renderers](#renderers). |
| `colorize` | `True` | Emit ANSI color when the selected renderer supports it. |
| `collapse_same_second` | `True` | Blank repeated timestamp seconds in console renderers. |
| `exception_show_locals` | `True` | Render redacted exception locals in tracebacks. |
| `extra_redact_patterns` | `()` | Additional field-name patterns redacted in logs. |
| `dependency_levels` | `None` | Overrides merged with Holylog's default dependency logger levels. |
| `dependency_handler_policy` | `"preserve"` | Whether dependency logger handlers are preserved or cleared. |
| `force` | `False` | Whether target logger handlers are replaced. |
| `logger` | `None` | Target root logger, logger name, or logger instance. |

`LoggingConfig` stores the normalized form after defaults are merged. Runtime
callers usually pass arguments to `setup_logging()` rather than constructing
`LoggingConfig` directly.

## Renderers

| Value | Output |
|---|---|
| `mini` | Compact human console output. |
| `cli` | CLI-oriented human console output. |
| `ipy` | Notebook-oriented human console output. |
| `json` | Machine-readable JSON records. |

`LoggingRenderer` is the literal union of those values.

## Handler Ownership

`setup_logging(force=False)` preserves host-owned handlers and updates only
Holylog-owned handlers. If a Holylog-owned handler already exists, its
formatter is replaced with the newly requested renderer and options, and its
stream is refreshed to the active `sys.stderr`.

`setup_logging(force=True)` clears all handlers from the target logger and
installs exactly one Holylog-owned stream handler.

When `logger` is a name or logger instance, Holylog configures that logger and
sets `propagate=False`. When `logger=None`, Holylog configures the root logger.

`dependency_levels={...}` sets dependency logger levels. Existing dependency
handlers and propagation are preserved unless
`dependency_handler_policy="clear"` is passed. The clear policy removes
dependency handlers and sets `propagate=True`.

## Semantic Events

`SEMANTIC_EVENTS` maps event names to `SemanticEvent` instances. Each event
stores the structured event name, stdlib transport level, icon, color role,
ellipsis behavior, and short usage text.

| Helper | Event | Stdlib Level | Use |
|---|---|---:|---|
| `LOG.trace(...)` | `TRACE` | `DEBUG` | Step-by-step debugging. |
| `LOG.debug(...)` | `DEBUG` | `DEBUG` | Verbose diagnostics. |
| `LOG.action_begin(...)` | `ACTION_BEGIN` | `INFO` | Begin a smaller action. |
| `LOG.action_success(...)` | `ACTION_SUCCESS` | `INFO` | Finish a smaller action. |
| `LOG.info_begin(...)` | `INFO_BEGIN` | `INFO` | Begin a larger task. |
| `LOG.info(...)` | `INFO` | `INFO` | General information. |
| `LOG.wait(...)` | `WAIT` | `INFO` | Waiting before retry or external work. |
| `LOG.save(...)` | `SAVE` | `INFO` | Saved data or persisted state. |
| `LOG.telemetry(...)` | `TELEMETRY` | `INFO` | Periodic runtime measurements. |
| `LOG.success(...)` | `SUCCESS` | `INFO` | Finish the script or major workflow. |
| `LOG.warning(...)` | `WARNING` | `WARNING` | Unexpected but recoverable condition. |
| `LOG.warn(...)` | `WARNING` | `WARNING` | Alias for `warning(...)`. |
| `LOG.retry(...)` | `RETRY` | `WARNING` | Retrying transient work. |
| `LOG.fallback(...)` | `FALLBACK` | `WARNING` | Using a fallback path. |
| `LOG.error(...)` | `ERROR` | `ERROR` | Non-fatal error. |
| `LOG.traceback(...)` | `TRACEBACK` | `ERROR` | Error with traceback. |
| `LOG.critical(...)` | `CRITICAL` | `CRITICAL` | Unrecoverable failure. |

Every semantic helper accepts:

- `msg` and optional printf-style `*args`
- `prefix=""`
- `extra_struct=None`
- stdlib logging controls such as `exc_info`, `stack_info`, `stacklevel`, and
  `extra`

`LOG.error(..., exc=exc)` and `LOG.traceback(..., exc=exc)` accept exception
objects as a convenience.

## Structured Fields

Use `extra_struct={...}` for fields intended for the structured formatter:

```python
LOG.success("loaded", extra_struct={"rows": 120})
```

Stdlib `extra={...}` is also supported. Holylog validates both mappings and
rejects keys that collide with reserved `LogRecord` attributes. Bare custom
keyword arguments are rejected.

Use `AppLogger.depth(depth)` around wrapper helpers that should shift reported
callsite attribution:

```python
with LOG.depth(1):
    LOG.info("called by wrapper")
```

## Correlation IDs

| API | Behavior |
|---|---|
| `cid_context(value=None)` | Context manager and async context manager that binds a CID and restores the previous value on exit. |
| `set_cid(value=None)` | Sets the current CID, creating one when `value` is `None`. |
| `new_cid()` | Returns a short random CID string. |
| `clear_cid()` | Clears the current CID. |

Holylog stores CIDs in a context variable and also binds them into structlog
contextvars so renderers can include `cid`.

## Telemetry

`async_telemetry(label="", interval=30.0, logger=None, include_threads=True,
extras=None)` returns an async context manager for periodic telemetry logs.

`with_async_telemetry(...)` decorates async functions and rejects non-async
functions at decoration time.

`AppLogger.telemetry_async(...)` creates the same context using the logger
instance as the telemetry logger.

The telemetry snapshot includes:

| Field | Meaning |
|---|---|
| `label` | Scope label. |
| `active_tasks_in_scope` | Active child tasks that inherited the telemetry scope. |
| `tasks_total` | Total tasks in the running event loop. |
| `threads` | Active OS thread count when `include_threads=True`. |

`extras` may return additional fields merged into telemetry snapshots and log
messages.

Telemetry uses contextvars to identify child tasks. It does not patch the event
loop's task creation methods.

## Lifecycle Logging

`log_init_lifecycle(label="Runtime Config", log_start=True, log_done=False)`
returns a class decorator. It wraps `__init__`, logs before construction when
`log_start=True`, calls the original initializer, and logs after construction
when `log_done=True`.

The wrapper is idempotent for a class that has already been decorated.

## Subprocess Output

`forward_cli_output(process, logger=None)` consumes `process.communicate()`,
logs stdout lines with `logger.info(...)`, logs stderr lines with
`logger.error(...)`, and returns the process return code.

Pass a `subprocess.Popen` instance configured with captured `stdout` and
`stderr`.

## Redaction

`REDACTED_VALUE` is the placeholder used for redacted values. The default value
is `[redacted]`.

Holylog redacts fields whose names match built-in secret-name patterns, such as
`token`, `secret`, `password`, `key`, and `DATABASE_URL`. Pass
`extra_redact_patterns=(...)` to `setup_logging()` to add project-specific
field-name patterns.

Structured event fields are traversed recursively through dictionaries, lists,
and tuples with a bounded depth and cycle protection. Redaction is based on
field names. Holylog does not scan arbitrary values for secret-looking text.

Rendered traceback locals are redacted by local-variable name.

## Project Paths

| Path | Purpose |
|---|---|
| `src/holylog/__init__.py` | Flat public facade. |
| `src/holylog/config.py` | `setup_logging()` and setup configuration. |
| `src/holylog/logger.py` | `AppLogger`, `get_logger()`, and logger class installation. |
| `src/holylog/events.py` | Semantic event registry and event metadata. |
| `src/holylog/context.py` | Correlation IDs and runtime record processors. |
| `src/holylog/rendering` | Console rendering, JSON exception rendering, and redaction. |
| `src/holylog/helpers` | Lifecycle, telemetry, and subprocess helper APIs. |
| `tests` | Behavior tests for public logging contracts. |
| `docs` | User and maintainer documentation. |
