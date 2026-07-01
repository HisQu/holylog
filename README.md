# Holylog

Stdlib-compatible semantic logging for Python applications.

## Table Of Contents

1. [Installation](#installation)
2. [Quickstart](#quickstart)
3. [Setup Model](#setup-model)
4. [Correlation IDs](#correlation-ids)
5. [Renderers](#renderers)
6. [Documentation](#documentation)
7. [Development](#development)

## Installation

```bash
python -m pip install holylog
```

For local development:

```bash
python -m pip install -e "." --group dev
```

## Quickstart

Use the flat package API:

```python
import holylog as hlog

hlog.setup_logging(level="INFO", renderer="cli")
LOG = hlog.get_logger()

LOG.success("configured", extra_struct={"profile": "default"})
```

`hlog.get_logger()` infers the caller module. Pass a name when explicit logger
ownership is clearer:

```python
LOG = hlog.get_logger(__name__)
```

Holylog loggers are real `logging.Logger` subclasses. They work with stdlib
handlers, `pytest` `caplog`, dependency loggers, and existing logging-aware
libraries while adding semantic helpers such as `success`, `action_begin`,
`retry`, `fallback`, `telemetry`, and `traceback`.

## Setup Model

`setup_logging()` is safe to call more than once. By default it updates only
Holylog's own handler, refreshes that handler's active `stderr` stream, and
leaves host-owned handlers attached. Use `force=True` only when Holylog should
take over the target logger and replace all of its handlers.

Use `logger="myapp"` to configure a named application logger instead of the
process root logger. Named logger setup disables propagation so embedded
applications can avoid taking over host logging.

Use `dependency_levels={...}` to adjust noisy dependency logger levels. Existing
dependency handlers are preserved by default; pass
`dependency_handler_policy="clear"` to clear dependency handlers and route those
records through propagation.

## Correlation IDs

Use `cid_context()` to bind a correlation ID for nested work and restore the
previous value automatically:

```python
with hlog.cid_context("request-42"):
    LOG.info("request started")
```

`cid_context()` works with `with` and `async with`. Use `set_cid()`,
`new_cid()`, and `clear_cid()` only when you intentionally want non-scoped CID
state.

## Renderers

Pass `renderer=...` to `setup_logging()`:

| Renderer | Output |
|---|---|
| `mini` | Compact human console output. |
| `cli` | CLI-oriented human console output. |
| `ipy` | Notebook-oriented human console output. |
| `json` | Machine-readable JSON records. |

## Documentation

- [Documentation map](docs/README.md)
- [How-To User Guides](docs/How-To-User-Guides.md)
- [References](docs/References.md)
- [Explanations](docs/Explanations.md)
- [Development](docs/Development.md)

## Development

```bash
python -m pip install -e "." --group dev
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/pytest
```

`uv`, `direnv`, and `just` may be used as local conveniences when available,
but the repository must remain installable with normal `pip`.
