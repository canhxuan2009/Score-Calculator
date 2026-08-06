"""Command-line entry point for Point Audit."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from point_audit import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser without performing application work."""
    parser = argparse.ArgumentParser(
        prog="point_audit",
        description="Kiểm tra và đối soát điểm thi đua từ Excel.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the placeholder CLI and return a process exit code."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

