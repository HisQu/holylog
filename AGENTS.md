# Repository conventions

## Repo routing

- Reuse existing helpers and utilities before adding new helper functions.
- Runtime logging behavior belongs in `src/holylog/logging`.
- The flat public facade belongs in `src/holylog/__init__.py`.
- Tests belong in `tests`.
- Long-form docs belong in `docs`.
- Check `TODO.md` before starting and remove resolved items when a pass handles
  them.

## Project rules

- Do not duplicate helpers or re-implement existing utilities without checking
  first.
- Keep `import holylog as hlog` as the primary user-facing API.
- Do not add `setup_logger`; the public setup function is `setup_logging`.
- For facade `__init__.py` files, prefer clean batch re-export imports plus
  file-level `# ruff: noqa: F401`.
- Update `README.md`, `docs`, and `CHANGELOG.md` when a change affects setup,
  public APIs, renderers, or user-visible output.
- Add minimal `__main__` demo code only when it improves discoverability or
  manual testing.

## Documentation rules

- Start major docs files with a compact table of contents.
- Use direct links and exact public names.
- Use GitHub callouts consistently.
- Do not put custom titles on the same line as a GitHub callout marker.

## Verification

- Review the diff for duplicate helpers, naming drift, unnecessary
  abstractions, and regressions.
- Run the project’s relevant lint, type-check, and test commands before
  considering the task done.

## User Decisions

- Never answer questions on the user's behalf.
- Do not treat defaults, timeouts, or auto-resolution as user approval.
- If a user decision is required, ask and wait for the user’s explicit answer.
