# References

## Table Of Contents

1. [Public API](#public-api)
2. [Renderers](#renderers)
3. [Semantic Events](#semantic-events)
4. [Setup Ownership](#setup-ownership)
5. [Project Paths](#project-paths)

## Public API

Import Holylog through the flat package facade:

```python
import holylog as hlog
```

| API | Purpose |
|---|---|
| `hlog.get_logger(name=None)` | Return an `AppLogger`; infers caller module when `name` is omitted. |
| `hlog.setup_logging(...)` | Configure stdlib handlers and structlog processors. |
| `hlog.AppLogger` | Stdlib logger subclass with semantic helpers. |
| `hlog.LoggingConfig` | Normalized logging setup dataclass. |
| `hlog.DependencyHandlerPolicy` | Dependency handler policy: `"preserve"` or `"clear"`. |
| `hlog.AppConsoleRenderer` | Human-readable renderer used by console modes. |
| `hlog.REDACTED_VALUE` | Placeholder used for redacted structured fields and locals. |
| `hlog.SEMANTIC_EVENTS` | Mapping of semantic event names to display metadata. |
| `hlog.SemanticEvent` | Dataclass describing one semantic event. |
| `hlog.cid_context(value=None)` | Scope a correlation ID and restore the previous value on exit. |
| `hlog.set_cid(value=None)` | Set or create a correlation ID. |
| `hlog.new_cid()` | Create a short random correlation ID. |
| `hlog.clear_cid()` | Clear the active correlation ID. |
| `hlog.log_init_lifecycle(...)` | Class decorator for initialization breadcrumbs. |
| `hlog.async_telemetry(...)` | Async context manager for periodic telemetry logs. |
| `hlog.with_async_telemetry(...)` | Async function decorator for telemetry logging. |
| `hlog.forward_cli_output(process, logger=...)` | Forward captured subprocess streams into logs. |

## Renderers

| Value | Output |
|---|---|
| `mini` | Compact human console output. |
| `cli` | CLI-oriented human console output. |
| `ipy` | Notebook-oriented human console output. |
| `json` | Machine-readable JSON records. |

## Semantic Events

Semantic helpers include `trace`, `debug`, `action_begin`, `action_success`,
`info_begin`, `info`, `wait`, `save`, `telemetry`, `success`, `warning`,
`retry`, `fallback`, `error`, `traceback`, and `critical`.

Structured fields belong in `extra_struct={...}` or stdlib `extra={...}`.
Holylog rejects fields that collide with reserved `LogRecord` attributes.

## Setup Ownership

`setup_logging(force=False)` preserves host-owned handlers and updates only
Holylog-owned handlers. `force=True` clears all target logger handlers and
installs one Holylog handler.

`dependency_levels={...}` sets dependency logger levels. Existing dependency
handlers and propagation are preserved unless
`dependency_handler_policy="clear"` is passed.

## Project Paths

| Path | Purpose |
|---|---|
| `src/holylog/logging` | Logging implementation modules. |
| `src/holylog/__init__.py` | Flat public facade. |
| `tests` | Behavior tests for public logging contracts. |
| `docs` | User and maintainer documentation. |
