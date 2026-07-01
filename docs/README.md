# Holylog Documentation

## Table Of Contents

1. [Reading Map](#reading-map)
2. [Documentation Contract](#documentation-contract)
3. [Repository Terms](#repository-terms)

## Reading Map

| Goal | Start Here |
|---|---|
| Add Holylog to an application | [How-To User Guides](How-To-User-Guides.md) |
| Choose setup options | [How-To User Guides](How-To-User-Guides.md#configure-logging) |
| Check exact public names and defaults | [References](References.md) |
| Understand how records move through logging | [Explanations](Explanations.md) |
| Change Holylog itself | [Development](Development.md) |

> [!NOTE]
> Related links:
> - Use [References](References.md) when code, docs, or downstream examples need
>   exact names.
> - Use [Development](Development.md) before changing packaging, tests, docs, or
>   release notes.

## Documentation Contract

Holylog docs are plain GitHub-rendered Markdown. Public examples should import
the flat facade:

```python
import holylog as hlog
```

Use exact public names from `holylog.__all__`. The public setup function is
`setup_logging()`.

## Repository Terms

| Term | Meaning |
|---|---|
| Holylog | This package, `holylog`, which provides semantic stdlib logging helpers and structlog-backed formatting. |
| semantic logger | A stdlib logger subclass with app-oriented helper methods such as `success`, `retry`, and `traceback`. |
| renderer | The final output mode selected by `setup_logging(renderer=...)`. |
| correlation ID | A context-local ID managed with `cid_context`, `set_cid`, `new_cid`, and `clear_cid`. |
| target logger | The root or named stdlib logger configured by `setup_logging(logger=...)`. |
| host-owned handler | A logging handler created outside Holylog. It is preserved unless `force=True` is used on the target logger. |
| Holylog-owned handler | A handler created and marked by Holylog. Repeated setup calls update this handler instead of adding duplicates. |
