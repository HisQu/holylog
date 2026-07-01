# Development

## Table Of Contents

1. [Setup](#setup)
2. [Verification](#verification)
3. [Repository Boundaries](#repository-boundaries)
4. [Documentation](#documentation)

## Setup

```bash
python -m pip install -e "." --group dev
```

`uv`, `direnv`, and `just` are convenience tools, but Holylog must remain
usable with standard Python packaging tools.

## Verification

Run the normal checks before finishing a change:

```bash
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/pytest
```

## Repository Boundaries

| Path | Responsibility |
|---|---|
| `src/holylog/logging` | Runtime logging implementation. |
| `src/holylog/__init__.py` | Flat public API facade. |
| `tests` | Public behavior and regression tests. |
| `docs` | GitHub-rendered docs. |

Keep new runtime behavior in `src/holylog/logging` unless it is only a facade
export in `src/holylog/__init__.py`.

## Documentation

Update `README.md`, `docs/`, and `CHANGELOG.md` when a change affects public
APIs, install commands, setup behavior, renderers, or user-visible output.
