# Changelog

All notable changes to `holylog` will be documented in this file.

## [Unreleased]

### 💥 Breaking Change Summary

No breaking changes yet.

### ➕ Added

- Added `DependencyHandlerPolicy` and the `dependency_handler_policy` option
  for explicit dependency logger handler takeover.

### 💔 Changed

- `setup_logging(force=False)` now preserves host-owned target handlers while
  updating Holylog-owned handlers in place. Use `force=True` for full target
  logger takeover.
- Dependency logger handlers are now preserved by default when applying
  `dependency_levels`; use `dependency_handler_policy="clear"` for the previous
  clear-and-propagate behavior.

### ⚠️ Deprecated

### 🗑️ Removed

### 🔨 Fixed

## 0.1.0 - 2026-07-01

### ➕ Added

- Released `holylog` as a pure logging library.
- Added the flat `import holylog as hlog` API with semantic stdlib loggers,
  structlog-backed formatting, JSON rendering, correlation IDs, lifecycle
  logging, telemetry helpers, and subprocess output forwarding.
