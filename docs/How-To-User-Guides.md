# How-To User Guides

## Table Of Contents

1. [Install Holylog](#install-holylog)
2. [Configure Logging](#configure-logging)
3. [Use Semantic Helpers](#use-semantic-helpers)
4. [Add Correlation IDs](#add-correlation-ids)
5. [Emit JSON Logs](#emit-json-logs)
6. [Redact Sensitive Fields](#redact-sensitive-fields)
7. [Log Initialization](#log-initialization)
8. [Track Async Telemetry](#track-async-telemetry)
9. [Forward Subprocess Output](#forward-subprocess-output)

## Install Holylog

```bash
python -m pip install holylog
```

For editable development:

```bash
python -m pip install -e "." --group dev
```

## Configure Logging

Call `setup_logging()` near the application entrypoint:

```python
import holylog as hlog

hlog.setup_logging(level="INFO", renderer="cli")
LOG = hlog.get_logger()

LOG.info("Application started")
```

Holylog updates the stdlib logging system. It installs `AppLogger` for future
loggers, configures one target logger, and attaches a Holylog-owned handler
with the selected renderer.

Configure a named application logger when the process root logger belongs to a
host application:

```python
hlog.setup_logging(level="DEBUG", logger="myapp")
LOG = hlog.get_logger("myapp")
```

Named setup disables propagation on that logger, so records do not also flow to
the root logger.

Use `force=True` only when Holylog should take over the target logger:

```python
hlog.setup_logging(level="INFO", renderer="json", force=True)
```

When `force=False`, Holylog preserves host-owned handlers and updates only the
handler it created. Repeated setup calls change Holylog formatting without
adding duplicate Holylog handlers.

Configure dependency logger levels without touching dependency handlers:

```python
import logging

hlog.setup_logging(dependency_levels={"httpx": logging.WARNING})
```

Pass `dependency_handler_policy="clear"` when a dependency should drop its own
handlers and propagate into the configured Holylog handler.

```python
hlog.setup_logging(
    dependency_levels={"httpx": logging.WARNING},
    dependency_handler_policy="clear",
)
```

## Use Semantic Helpers

```python
import holylog as hlog

LOG = hlog.get_logger()

LOG.action_begin("Loading workspace")
LOG.success("Workspace ready", extra_struct={"workspace": "default"})
```

Semantic helpers are stdlib log calls with stable event metadata. They choose
the transport level, icon, console color role, and `event_type`.

Common helpers:

| Helper | Use |
|---|---|
| `LOG.trace(...)` | Step-by-step debugging. |
| `LOG.debug(...)` | Verbose diagnostics. |
| `LOG.action_begin(...)` | Start a smaller action. |
| `LOG.action_success(...)` | Finish a smaller action. |
| `LOG.info_begin(...)` | Start a larger task. |
| `LOG.info(...)` | General information. |
| `LOG.wait(...)` | Waiting before retry or external work. |
| `LOG.save(...)` | Saved data or persisted state. |
| `LOG.telemetry(...)` | Periodic runtime measurements. |
| `LOG.success(...)` | Complete the script or major workflow. |
| `LOG.warning(...)` | Unexpected but recoverable condition. |
| `LOG.retry(...)` | Retrying transient work. |
| `LOG.fallback(...)` | Using a fallback path. |
| `LOG.error(...)` | Non-fatal error. |
| `LOG.traceback(...)` | Error with traceback. |
| `LOG.critical(...)` | Unrecoverable failure. |

Pass structured fields through `extra_struct={...}`:

```python
LOG.retry(
    "download failed",
    extra_struct={"attempt": 2, "max_attempts": 5},
)
```

Stdlib control keywords such as `exc_info`, `stack_info`, `stacklevel`, and
`extra` remain available. Bare custom keyword arguments are rejected so log
calls stay close to stdlib logging.

Use `traceback()` in exception handlers:

```python
try:
    load_config()
except ValueError as exc:
    LOG.traceback("Could not load config", exc=exc)
```

## Add Correlation IDs

Bind correlation IDs around request, job, or batch scopes:

```python
with hlog.cid_context("request-42"):
    LOG.info("request started")
```

Omit the value to create a fresh ID:

```python
with hlog.cid_context() as cid:
    LOG.info("created scoped CID", extra_struct={"cid": cid})
```

Use `async with` inside async request handlers:

```python
async with hlog.cid_context("request-42"):
    LOG.info("async request started")
```

The context manager restores the previous CID on exit, including restoring
`None` when no outer CID existed. Use `set_cid()`, `new_cid()`, and
`clear_cid()` when the CID should outlive a single context manager scope.

## Emit JSON Logs

```python
hlog.setup_logging(renderer="json", colorize=False)
LOG = hlog.get_logger()
LOG.info("batch complete", extra_struct={"rows": 42})
```

JSON output includes standard record metadata, semantic event fields, context
values such as `cid`, and redacted exception locals.

Use JSON rendering for files, process supervisors, log collectors, and test
fixtures that need stable machine-readable fields. Use `cli`, `mini`, or `ipy`
for humans reading a terminal or notebook.

## Redact Sensitive Fields

Holylog redacts fields whose names match built-in secret patterns, such as
`token`, `secret`, `password`, `key`, and `DATABASE_URL`.

```python
hlog.setup_logging(
    renderer="json",
    extra_redact_patterns=("private", "credential"),
)

LOG.info(
    "connected",
    extra_struct={
        "DATABASE_URL": "postgres://example",
        "user": "service",
    },
)
```

The redacted value is `hlog.REDACTED_VALUE`, currently `[redacted]`.

Structured-field redaction is recursive for dictionaries, lists, and tuples up
to a bounded depth. Matching keys are replaced before JSON serialization, so
secret values may be strings, numbers, objects, or other non-serializable
values.

Redaction is based on field names, not value scanning. A value under a safe key
is left alone even when the value text looks secret.

Set `exception_show_locals=False` when exception locals should never be
rendered:

```python
hlog.setup_logging(exception_show_locals=False)
```

## Log Initialization

Use `log_init_lifecycle()` on classes that should emit construction
breadcrumbs:

```python
@hlog.log_init_lifecycle(label="Runtime Config", log_done=True)
class RuntimeConfig:
    def __init__(self, profile: str) -> None:
        self.profile = profile
```

The decorator wraps `__init__`, emits an optional start message, calls the
original initializer, then emits an optional done message.

## Track Async Telemetry

Use `async_telemetry()` around async work to log task and thread counters at an
interval:

```python
async with hlog.async_telemetry("sync-users", interval=10.0):
    await sync_users()
```

Pass an `extras` callback for additional numeric or textual counters:

```python
cache: dict[str, object] = {}


def cache_metrics() -> dict[str, object]:
    return {"cache_size": len(cache)}


async with hlog.async_telemetry("cache-warmup", extras=cache_metrics):
    await warm_cache()
```

Decorate an async function with `with_async_telemetry()`:

```python
@hlog.with_async_telemetry("sync-users", interval=10.0)
async def sync_users() -> None:
    ...
```

> [!WARNING]
> The current telemetry implementation patches the running event loop's
> `create_task` method while the context is active. Nested or overlapping
> telemetry contexts are tracked as a TODO for a later design pass.

## Forward Subprocess Output

Use `forward_cli_output()` when a subprocess has captured stdout and stderr:

```python
import subprocess

process = subprocess.Popen(
    ["python", "--version"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

return_code = hlog.forward_cli_output(process, logger=LOG)
```

Stdout lines are logged with `LOG.info(...)`. Stderr lines are logged with
`LOG.error(...)`. The helper consumes `process.communicate()` exactly once and
returns the child process return code.
