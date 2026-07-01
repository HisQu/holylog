# Todo list

Treat this as the parking lot for actionable problems discovered while working but intentionally left unresolved.


<br>

> [!CAUTION]
> This is git-tracked: Never record secrets, absolute paths, credentials, private host data, or speculative security claims. Use only relative paths.


> [!IMPORTANT]
>
> ## Rules
> 1) Do not remove or change this header and TOC without very good reason.
> 1) Newest at the top.
> 1) Append a new entry only when the observation is real, actionable, not already listed, and out of scope for the current change. Do not modify `TODO.md` when there is nothing useful to add.
> 1) If an issue is new and related to another issue, reference it in the `Suggested next step`. Do not create a new entry for the same problem. Place the reference in both entries (bi-directional).
> 1) If an issue was resolved, remove it and make an entry in the CHANGELOG.md.
> 1) **Types:**
>       - **Bug risk**: Potential defect with concrete evidence, not yet confirmed.
>       - **Code smell**: Implementation, architectural, maintainability or clarity issue that is not currently a defect.
>       - **Docs drift**: Documentation is stale, incomplete, or inconsistent.
>       - **Tooling**: Issue with build, test, lint, type-check, and general slowdown of developer workflow.
>       - **Security**: Evidence-backed security risk. Use Question for uncertainty.
>       - **Question**: Design, behavior, or ownership uncertainty needing investigation.
>
> 1) **Priorities:**
>       - **P1**: Should be handled ASAP.
>       - **P2**: Should be handled before next release or milestone.
>       - **P3**: Useful cleanup for a later focused pass.
> 1) **Effort:**
>       - **E1**: Issue deserves its own focused pass.
>       - **E2**: Can be batched with a few other issues.
>       - **E3**: Can be batched with many other issues.
> 1) **Format:**
> ```markdown
>
> <br>
>
> # YYYY-MM-DD
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Area:** `path/or/symbol`
> - **Observed while:** short context
> - **Evidence:** concrete observation
> - **Why not fixed now:** scope, risk, uncertainty, or user decision needed
> - **Suggested next step:** smallest reasonable follow-up. If applicable, reference related todos [here](#todo-list).
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Area:** `path/or/symbol`
> - ...
>
> <br>
>
> # YYYY-MM-DD
>
> ## <Priority> / <Effort> [<Type>] - *Short problem title*
> - **Area:** `path/or/symbol`
> - ...
> ```


<br>

---

<br>

## Table Of Contents

1. [Todo list](#todo-list)
   1. [Table Of Contents](#table-of-contents)
2. [2026-07-01](#2026-07-01)
   1. [P3 / E3 \[Code smell\] - remove useless nesting](#p3--e3-code-smell---remove-useless-nesting)
   2. [P2 / E1 \[Code smell\] - *Async telemetry patches the event loop method*](#p2--e1-code-smell---async-telemetry-patches-the-event-loop-method)
   3. [P3 / E1 \[Code smell\] - *Structlog compatibility layer still reads as optional*](#p3--e1-code-smell---structlog-compatibility-layer-still-reads-as-optional)

<br>

---

<br>

# 2026-07-01

## P3 / E3 [Code smell] - remove useless nesting
- The `holylog.logging` level is currently useless. Find a better architecture.

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
