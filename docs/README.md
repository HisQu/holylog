# Holylog Documentation

## Table Of Contents

1. [Reading Map](#reading-map)
2. [Repository Terms](#repository-terms)

## Reading Map

| Goal | Start Here |
|---|---|
| Add logging to an app | [How-To User Guides](How-To-User-Guides.md) |
| Check exact public names | [References](References.md) |
| Understand the design | [Explanations](Explanations.md) |
| Maintain the repo | [Development](Development.md) |

> [!NOTE]
> Related links:
> - Use [References](References.md) for exact API names.
> - Use [Development](Development.md) before changing packaging or docs.

## Repository Terms

| Term | Meaning |
|---|---|
| Holylog | This package, `holylog`, which provides semantic stdlib logging helpers and structlog-backed formatting. |
| semantic logger | A stdlib logger subclass with app-oriented helper methods such as `success`, `retry`, and `traceback`. |
| renderer | The final output mode selected by `setup_logging(renderer=...)`. |
| correlation ID | A context-local ID managed with `cid_context`, `set_cid`, `new_cid`, and `clear_cid`. |
