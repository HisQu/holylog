"""Print a small import smoke-test message for ``python -m holylog``."""

from __future__ import annotations

from importlib import metadata


def main() -> None:
    """Print the installed Holylog version.

    :return: ``None``.
    """

    try:
        version = metadata.version("holylog")
    except metadata.PackageNotFoundError:
        version = "0.1.0"
    print(f"holylog {version}")


if __name__ == "__main__":
    main()
