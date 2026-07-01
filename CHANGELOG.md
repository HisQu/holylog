# Changelog

All notable changes to `holylog` will be documented in this file.

> [!IMPORTANT]
> ## Rules
> 1) Do not remove or change this header and TOC without very good reason.
> 1) When bumping version, move the sub-sections from `[Unreleased]` to
>    the new version -section. Remove empty sub-sections under released
>    versions. Provide a new `[Unreleased]` section at the top of the
>    changelog with all sections empty (don't remove those).
> 1) Do not remove emojis and use `<br>` and `---`.
> 1) Changelog entries must describe the final net difference from the
>    previous released version. Do not list intermediate pre-release
>    names, helper shapes, fixes, or refactors that were overwritten
>    before release.
> 1) Use `🔨 Fixed` only for defects in previously released behavior.
>    For new features, describe the final shipped behavior under `➕
>    Added`, even if the implementation went through pre-release fixes.



<br>

---

<br>

## Table Of Contents

1. [Changelog](#changelog)
   1. [Table Of Contents](#table-of-contents)
   2. [\[Unreleased\]](#unreleased)
   3. [0.1.0 - 2026-07-01](#010---2026-07-01)

<br>

---

<br>

<!-- ======================================================== -->


## [Unreleased]

### 💥 Breaking Change Summary

- Breaking: Removed the nested `holylog.logging` package and moved internals
  into clearer modules such as `holylog.config`, `holylog.logger`,
  `holylog.events`, `holylog.context`, `holylog.rendering`, and
  `holylog.helpers`.
  Affected: Users importing `holylog.logging` or `holylog.logging.*` internals.
  Migration: Use the flat public facade, `import holylog as hlog`; maintainers
  can use the new internal module paths when needed.

### ➕ Added

- Added `cid_context()` for scoped sync and async correlation IDs that restore
  the previous CID on exit.
- Added `DependencyHandlerPolicy` and the `dependency_handler_policy` option
  for explicit dependency logger handler takeover.

### 💔 Changed

- Reorganized Holylog internals into clearer top-level modules and
  domain-named subpackages while preserving the flat `import holylog as hlog`
  facade.
- Structlog support is now modeled as a required runtime dependency through a
  compatibility helper with friendly missing/incompatible dependency errors.
  CID helpers no longer silently skip structlog context binding.
- Async telemetry now tracks scoped child tasks with contextvars instead of
  patching the event loop's `create_task` method. Nested and overlapping
  telemetry contexts now have regression coverage.
- Structured-field redaction now recursively traverses nested dictionaries,
  lists, and tuples with bounded depth and cycle protection. Semantic helper
  coverage now asserts that public helper methods stay aligned with
  `SEMANTIC_EVENTS`.
- Expanded the README and docs into a complete first-pass guide covering setup
  ownership, semantic helpers, correlation IDs, JSON output, redaction,
  lifecycle logging, telemetry, subprocess forwarding, and maintainer workflow.
- `setup_logging(force=False)` now preserves host-owned target handlers while
  updating Holylog-owned handlers in place. Use `force=True` for full target
  logger takeover.
- Dependency logger handlers are now preserved by default when applying
  `dependency_levels`; use `dependency_handler_policy="clear"` for the previous
  clear-and-propagate behavior.

### ⚠️ Deprecated

### 🗑️ Removed

- Removed the nested `holylog.logging` implementation package.

### 🔨 Fixed

## 0.1.0 - 2026-07-01

### ➕ Added

- Released `holylog` as a pure logging library.
- Added the flat `import holylog as hlog` API with semantic stdlib loggers,
  structlog-backed formatting, JSON rendering, correlation IDs, lifecycle
  logging, telemetry helpers, and subprocess output forwarding.
