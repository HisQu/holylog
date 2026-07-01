# Explanations

## Table Of Contents

1. [Design Model](#design-model)
2. [Why Stdlib Logging](#why-stdlib-logging)
3. [Formatting Pipeline](#formatting-pipeline)
4. [Handler Ownership](#handler-ownership)
5. [Correlation IDs](#correlation-ids)
6. [Redaction Scope](#redaction-scope)
7. [Async Telemetry](#async-telemetry)
8. [Flat Facade](#flat-facade)

## Design Model

Holylog separates emission from formatting.

Application code emits through `AppLogger`, a real `logging.Logger` subclass.
Semantic methods choose a stdlib level, message decoration, icon, color role,
and structured metadata. The record still travels through stdlib logging, so
existing handlers, `pytest` `caplog`, and dependency loggers behave normally.

`setup_logging()` owns Holylog's formatting path. It installs Holylog's logger
class for future loggers, configures a root or named stdlib logger, and
attaches a structlog `ProcessorFormatter` to a marked handler for console or
JSON output. Repeated setup calls update that marked handler without disturbing
host-owned handlers unless `force=True` is used.

This keeps the call site small:

```python
import holylog as hlog

hlog.setup_logging()
LOG = hlog.get_logger()
```

Application modules then keep using a normal logger object. The extra behavior
comes from the installed logger class and formatter pipeline, not from a custom
logging transport.

## Why Stdlib Logging

Most Python libraries already speak stdlib logging. Holylog keeps that
transport so application logs and dependency logs can share one handler tree.
The semantic API adds richer events without asking callers to adopt a separate
logging object model.

This also keeps test and host integration familiar:

- `pytest` `caplog` can capture records.
- Existing `logging.Handler` instances still work.
- Dependency loggers keep their normal stdlib level and propagation behavior.
- Applications can configure root logging or a named logger.

## Formatting Pipeline

The formatter enriches records with:

- stdlib metadata such as logger name, level, line, and function
- async task or thread name
- correlation ID context
- semantic display defaults
- redacted structured fields and exception locals

Use `cid_context()` for nested request or batch scopes that should restore the
previous correlation ID automatically.

The final renderer then emits human console text or JSON.

Console renderers use `AppConsoleRenderer`. JSON rendering uses structlog's
JSON renderer after Holylog has added stdlib and semantic fields.

## Handler Ownership

Earlier AppRC logging setup was more willing to clear handlers. Holylog is a
library, so the default is now conservative.

When `force=False`, `setup_logging()` owns only handlers created by Holylog. A
host application, test harness, or dependency may already have handlers on the
target logger. Holylog leaves those handlers in place and either updates an
existing Holylog-owned handler or appends one.

When `force=True`, the caller is saying that Holylog owns the selected target
logger. Holylog clears that logger's handlers and installs one Holylog-owned
handler. This behavior is intentionally strong and should be used near an
application entrypoint, not in a reusable library.

Dependency logger setup is separate. `dependency_levels` always applies levels.
Dependency handlers and propagation are preserved unless
`dependency_handler_policy="clear"` is selected.

## Correlation IDs

Correlation IDs identify a request, job, batch, or other unit of work across
many log records. Holylog stores the current CID in a context variable and also
binds it into structlog contextvars so the formatter can render the same value.

`cid_context()` is the preferred API because it restores the prior value:

```python
with hlog.cid_context("outer"):
    LOG.info("outer")
    with hlog.cid_context("inner"):
        LOG.info("inner")
    LOG.info("outer restored")
```

`set_cid()` and `clear_cid()` are intentionally lower-level. Use them when the
CID lifecycle is owned elsewhere and should not be tied to a Python context
manager.

## Redaction Scope

Holylog redacts by field name. Secret-looking names are replaced with
`REDACTED_VALUE` before rendering. The same matcher is used for normal event
fields and traceback locals.

Structured event fields are traversed recursively through dictionaries, lists,
and tuples with a bounded depth and cycle protection. Nested containers are
copied only when a value changes, so ordinary scalar-heavy log records avoid
extra allocation.

> [!WARNING]
> Redaction does not inspect arbitrary values. Put secrets under clearly named
> fields such as `token`, `api_key`, `password`, `secret`, or a project-specific
> pattern passed with `extra_redact_patterns`.

## Async Telemetry

Async telemetry counts child tasks that inherit the active telemetry scope.
Holylog stores the active scope stack in a context variable. Python copies
context variables into newly created tasks, so tasks started inside a telemetry
block carry that scope without any event-loop monkeypatching.

Snapshots inspect task contexts with `asyncio.Task.get_context()`, exclude
Holylog's reporter task and the owning task, and count active child tasks that
contain the scope. Nested telemetry scopes are represented as a scope stack, so
a task created inside an inner scope can be counted by both the inner and outer
telemetry contexts.

## Flat Facade

User code should import the package facade:

```python
import holylog as hlog
```

The nested `holylog.logging` package currently owns the implementation modules,
but it is not the preferred user-facing import path. A future architecture pass
may remove useless nesting while preserving the flat facade where practical.
