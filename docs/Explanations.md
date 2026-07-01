# Explanations

## Table Of Contents

1. [Design Model](#design-model)
2. [Why Stdlib Logging](#why-stdlib-logging)
3. [Formatting Pipeline](#formatting-pipeline)

## Design Model

Holylog separates emission from formatting.

Application code emits through `AppLogger`, a real `logging.Logger` subclass.
Semantic methods choose a stdlib level, message decoration, icon, color role,
and structured metadata. The record still travels through stdlib logging, so
existing handlers, `pytest` `caplog`, and dependency loggers behave normally.

`setup_logging()` owns the formatting path. It installs Holylog's logger class
for future loggers, configures a root or named stdlib logger, and attaches a
structlog `ProcessorFormatter` for console or JSON output.

## Why Stdlib Logging

Most Python libraries already speak stdlib logging. Holylog keeps that
transport so application logs and dependency logs can share one handler tree.
The semantic API adds richer events without asking callers to adopt a separate
logging object model.

## Formatting Pipeline

The formatter enriches records with:

- stdlib metadata such as logger name, level, line, and function
- async task or thread name
- correlation ID context
- semantic display defaults
- redacted structured fields and exception locals

The final renderer then emits human console text or JSON.
