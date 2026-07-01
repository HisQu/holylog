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

## Use Semantic Helpers

```python
import holylog as hlog

LOG = hlog.get_logger()

LOG.action_begin("Loading workspace")
LOG.success("Workspace ready", extra_struct={"workspace": "default"})
```

Pass structured fields through `extra_struct={...}`. Bare custom keyword
arguments are rejected so calls stay close to stdlib logging.

## Emit JSON Logs

```python
hlog.setup_logging(renderer="json", colorize=False)
LOG = hlog.get_logger()
LOG.info("batch complete", extra_struct={"rows": 42})
```

JSON output includes standard record metadata, semantic event fields, context
values such as `cid`, and redacted exception locals.
