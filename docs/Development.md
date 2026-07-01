# Development

## Table Of Contents

1. [Setup](#setup)
2. [Verification](#verification)
3. [Repository Boundaries](#repository-boundaries)
4. [Documentation Work](#documentation-work)
5. [TODO Workflow](#todo-workflow)
6. [Changelog Workflow](#changelog-workflow)
7. [Release Notes](#release-notes)

## Setup

```bash
python -m pip install -e "." --group dev
```

`uv`, `direnv`, and `just` are convenience tools, but Holylog must remain
usable with standard Python packaging tools.

The package requires Python 3.12 or newer. Runtime dependencies are `rich` and
`structlog>=25.5`.

## Verification

Run the normal checks before finishing a change:

```bash
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/pyright
.venv/bin/pytest
```

For documentation-only changes, still run the standard checks unless the change
is truly mechanical and the maintainer explicitly narrows verification. Docs
often contain import names, public function names, and examples that drift from
tests.

Useful consistency searches:

```bash
rg "import holylog as hlog" README.md docs
rg "setup_logging" README.md docs
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

The preferred public import is:

```python
import holylog as hlog
```

The public setup function is `setup_logging()`.

## Documentation Work

Update `README.md`, `docs/`, and `CHANGELOG.md` when a change affects public
APIs, install commands, setup behavior, renderers, or user-visible output.

Use this split:

| File | Role |
|---|---|
| `README.md` | Short package landing page and quickstart. |
| `docs/README.md` | Reading map and glossary. |
| `docs/How-To-User-Guides.md` | Task recipes users can copy from. |
| `docs/References.md` | Exact public API names, defaults, and behavior. |
| `docs/Explanations.md` | Design reasoning and caveats. |
| `docs/Development.md` | Maintainer workflow. |

Major docs files should start with a compact table of contents. Use exact
public names and direct links. Use GitHub callouts for warnings and required
context.

## TODO Workflow

Read `TODO.md` before starting a pass. If a pass resolves a TODO item, remove
that item and add a changelog entry. Do not leave resolved parking-lot entries
behind.

Add a TODO only when the issue is real, actionable, not already listed, and out
of scope for the current change. Use only relative paths and avoid secrets,
hostnames, credentials, or private machine details.

## Changelog Workflow

Keep changes under `[Unreleased]` until a release pass moves them to a version
section. Use the existing section order and emojis.

Breaking changes must be explicit and include:

- what changed
- who is affected
- how to migrate

Do not hide breaking changes under generic cleanup language.

## Release Notes

Holylog is young and currently exposes a small flat API. Release notes should
describe the final user-visible behavior, not every intermediate helper name or
private refactor from a development pass.
