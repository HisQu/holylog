# Todo List

Treat this as the parking lot for actionable problems discovered while working
but intentionally left unresolved.

> [!CAUTION]
> This is git-tracked: never record secrets, absolute paths, credentials,
> private host data, or speculative security claims. Use only relative paths.

> [!IMPORTANT]
>
> ## Rules
>
> 1. Newest entries go at the top.
> 2. Add an entry only when the observation is real, actionable, not already
>    listed, and out of scope for the current change.
> 3. Remove resolved issues and mention the resolution in `CHANGELOG.md`.
> 4. Use the type labels `Bug risk`, `Code smell`, `Docs drift`, `Tooling`,
>    `Security`, or `Question`.
> 5. Use priorities `P1` for soon, `P2` for before the next milestone, and
>    `P3` for later cleanup.
> 6. Use effort labels `E1` for a focused pass, `E2` for a small batch, and
>    `E3` for a large batch.

<br>

---

<br>

## Table Of Contents

1. [Todo List](#todo-list)
   1. [Table Of Contents](#table-of-contents)
2. [[0.1.0] 2026-07-01](#010-2026-07-01)
   1. [P1 / E1 [Code smell] - `setup_logging()` handler ownership is too blunt](#p1--e1-code-smell---setup_logging-handler-ownership-is-too-blunt)
   2. [P1 / E2 [Code smell] - CID lifecycle cannot restore an outer value](#p1--e2-code-smell---cid-lifecycle-cannot-restore-an-outer-value)
   3. [P2 / E1 [Code smell] - Async telemetry patches the event loop method](#p2--e1-code-smell---async-telemetry-patches-the-event-loop-method)
   4. [P2 / E2 [Code smell] - Redaction policy is shallow for structured fields](#p2--e2-code-smell---redaction-policy-is-shallow-for-structured-fields)
   5. [P2 / E3 [Code smell] - Semantic event methods can drift from the registry](#p2--e3-code-smell---semantic-event-methods-can-drift-from-the-registry)
   6. [P3 / E1 [Code smell] - Structlog compatibility layer still reads as optional](#p3--e1-code-smell---structlog-compatibility-layer-still-reads-as-optional)

<br>

---

<br>

# [0.1.0] 2026-07-01

## P1 / E1 [Code smell] - *`setup_logging()` handler ownership is too blunt*

- **Area:** `src/holylog/logging/config.py`
- **Observed while:** Holylog split code-smell pass.
- **Evidence:** `_configure_stdlib()` returns early when the target logger has
  handlers and `force=False`, so later calls update only the level and ignore
  renderer, color, redaction, exception-local, and stream changes. With
  `force=True`, Holylog clears every target handler. `_configure_dependency_loggers()`
  also clears every configured dependency logger handler before enabling
  propagation.
- **Why not fixed now:** Better handler ownership needs a small policy design:
  tag Holylog-owned handlers, update only those handlers in place, and decide
  how named logger setup should coexist with host-owned handlers.
- **Suggested next step:** Add a private Holylog handler marker, update existing
  Holylog handlers instead of all handlers, and add tests for repeated setup
  calls with different renderers plus host-owned sentinel handlers.

## P1 / E2 [Code smell] - *CID lifecycle cannot restore an outer value*

- **Area:** `src/holylog/logging/context.py`
- **Observed while:** Holylog split code-smell pass.
- **Evidence:** `set_cid()` stores a new value and returns only the string.
  `clear_cid()` always sets the context variable to `None`. Callers cannot use
  the `ContextVar` token to restore a previous CID after nested request, batch,
  or test scopes.
- **Why not fixed now:** Changing `set_cid()`'s return value would be a public
  API change, and the split intentionally kept the migrated API stable.
- **Suggested next step:** Add a `cid_context(value=None)` context manager or a
  token-returning helper, keep `set_cid()` returning `str`, and test nested CID
  scopes across sync and async call paths.

## P2 / E1 [Code smell] - *Async telemetry patches the event loop method*

- **Area:** `src/holylog/logging/functions/telemetry.py`
- **Observed while:** Holylog split code-smell pass.
- **Evidence:** `AsyncTelemetryContext._start()` assigns a wrapper directly to
  `loop.create_task`. Nested or concurrent telemetry contexts on the same loop
  can overwrite each other's saved method. The synchronous `with` exit restores
  the method and signals the reporter, but cannot await the reporter task.
- **Why not fixed now:** Reworking telemetry needs a design pass and behavior
  tests for nested contexts, overlapping contexts, cancellation, and sync
  context-manager usage inside a running loop.
- **Suggested next step:** Replace direct method patching with a narrower task
  tracking strategy, or explicitly document and enforce one active telemetry
  context per loop. Add tests for nested contexts before changing behavior.

## P2 / E2 [Code smell] - *Redaction policy is shallow for structured fields*

- **Area:** `src/holylog/logging/exceptions.py`
- **Observed while:** Holylog split code-smell pass.
- **Evidence:** `LogFieldRedactor` checks only top-level event keys. Traceback
  local-variable redaction walks extracted frame-local mappings, but structured
  values nested inside `extra_struct` dictionaries or lists are not traversed.
  Current tests cover top-level event fields and traceback locals only.
- **Why not fixed now:** Recursive redaction needs clear limits for depth,
  mapping/list handling, object representation, and performance before it
  becomes formatter hot-path behavior.
- **Suggested next step:** Add a bounded recursive redaction helper for JSON and
  console structured fields, document the exact redaction scope, and test nested
  mappings, lists, tuples, and non-serializable values.

## P2 / E3 [Code smell] - *Semantic event methods can drift from the registry*

- **Area:** `src/holylog/logging/core.py`, `src/holylog/logging/levels.py`
- **Observed while:** Holylog split code-smell pass.
- **Evidence:** `SEMANTIC_EVENTS` is the event registry, but each public method
  on `AppLogger` repeats the same wrapper signature and hard-codes the event
  name. Adding, renaming, or removing an event requires coordinated edits in
  the registry, logger class, docs, and tests.
- **Why not fixed now:** The explicit methods are useful for autocomplete and
  type checkers, so replacing them with dynamic methods would be a tradeoff.
- **Suggested next step:** Keep explicit public methods, but add a small
  internal helper or table-driven test that asserts every supported public
  semantic method maps to an event and every event intended for callers has a
  method.

## P3 / E1 [Code smell] - *Structlog compatibility layer still reads as optional*

- **Area:** `src/holylog/logging/_optional.py`,
  `src/holylog/logging/context.py`, `src/holylog/logging/config.py`
- **Observed while:** Holylog split code-smell pass.
- **Evidence:** Holylog now declares `structlog>=25.5` as a normal runtime
  dependency, but `_optional.py` still models structlog as optional through
  helpers named `optional_structlog_contextvars()` and `require_structlog()`.
  `set_cid()` silently skips structlog context binding when the root package is
  missing, while `setup_logging()` raises.
- **Why not fixed now:** The migrated code kept AppRC's optional-extra boundary
  intact to reduce split risk.
- **Suggested next step:** Rename the module to compatibility/validation
  language, import required structlog pieces directly where reasonable, and
  keep only version/feature checks that produce better user errors than the
  default import failure.
