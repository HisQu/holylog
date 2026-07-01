# Holylog

Stdlib-compatible semantic logging for Python applications.

## Table Of Contents

1. [Installation](#installation)
2. [Usage](#usage)
3. [Development](#development)
4. [Documentation](#documentation)

## Installation

```bash
python -m pip install holylog
```

For local development:

```bash
python -m pip install -e "." --group dev
```

## Usage

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

`setup_logging()` is safe to call more than once. By default it updates only
Holylog's own handler and leaves host-owned handlers attached. Use
`force=True` only when Holylog should take over the target logger and replace
all of its handlers.

Use `dependency_levels={...}` to adjust noisy dependency logger levels. Existing
dependency handlers are preserved by default; pass
`dependency_handler_policy="clear"` to clear dependency handlers and route those
records through propagation.

Available renderers for `setup_logging(renderer=...)`:

| Renderer | Output |
|---|---|
| `mini` | Compact human console output. |
| `cli` | CLI-oriented human console output. |
| `ipy` | Notebook-oriented human console output. |
| `json` | Machine-readable JSON records. |

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

## Documentation

- [How-To User Guides](docs/How-To-User-Guides.md)
- [References](docs/References.md)
- [Explanations](docs/Explanations.md)
- [Development](docs/Development.md)
