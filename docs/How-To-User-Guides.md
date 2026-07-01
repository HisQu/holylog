# How-To User Guides

## Table Of Contents

1. [Install Holylog](#install-holylog)
2. [Configure Logging](#configure-logging)
3. [Use Semantic Helpers](#use-semantic-helpers)
4. [Emit JSON Logs](#emit-json-logs)

## Install Holylog

```bash
python -m pip install holylog
```

For editable development:

```bash
python -m pip install -e "." --group dev
```

## Configure Logging

Call `setup_logging()` once near the application entrypoint:

```python
import holylog as hlog

hlog.setup_logging(level="INFO", renderer="cli")
LOG = hlog.get_logger()

LOG.info("Application started")
```

Use `logger="myapp"` when embedding an application inside a host process that
owns root logging:

```python
hlog.setup_logging(level="DEBUG", logger="myapp", force=True)
```

When `force=False`, Holylog updates only its own marked handler and preserves
host-owned handlers. Use `force=True` only when the application intentionally
takes over the selected target logger.

Configure dependency logger levels without touching dependency handlers:

```python
import logging

hlog.setup_logging(dependency_levels={"httpx": logging.WARNING})
```

Pass `dependency_handler_policy="clear"` when a dependency should drop its own
handlers and propagate into the configured Holylog handler.

## Use Semantic Helpers

```python
import holylog as hlog

LOG = hlog.get_logger()

LOG.action_begin("Loading workspace")
LOG.success("Workspace ready", extra_struct={"workspace": "default"})
```

Pass structured fields through `extra_struct={...}`. Bare custom keyword
arguments are rejected so calls stay close to stdlib logging.

Bind correlation IDs around request, job, or batch scopes:

```python
with hlog.cid_context("request-42"):
    LOG.info("request started")
```

`cid_context()` also works with `async with` and restores any outer CID on exit.

## Emit JSON Logs

```python
hlog.setup_logging(renderer="json", colorize=False)
LOG = hlog.get_logger()
LOG.info("batch complete", extra_struct={"rows": 42})
```

JSON output includes standard record metadata, semantic event fields, context
values such as `cid`, and redacted exception locals.
