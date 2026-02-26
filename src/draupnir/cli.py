"""Draupnir CLI — generate JSON Schema from Verdandi YAML.

Default mode is --all (generate everything). Single-schema mode
exists for debugging only.
"""

import argparse
import sys
from pathlib import Path

from draupnir.functions.impure.pipeline import (
    resolve_paths,
    run_all,
    run_check,
    run_list,
)


def find_workspace_root() -> Path:
    """Find the workspace root by walking up from this file's location.

    Identifies the workspace root as the first ancestor containing
    tools/verdandi/. Falls back to the draupnir tool root's grandparent.
    """
    start = Path(__file__).resolve().parent
    for parent in start.parents:
        if (parent / "tools" / "verdandi").is_dir():
            return parent
    return start.parents[3]


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="draupnir",
        description="Generate JSON Schema from Verdandi YAML.",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Generate all schemas (default)",
    )
    group.add_argument(
        "--check",
        action="store_true",
        help="Check for drift without writing",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="List available schemas",
    )
    parser.add_argument(
        "--verdandi-dir",
        type=Path,
        default=None,
        help="Override Verdandi root directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Override output directory",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Override workspace root",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    workspace = args.workspace or find_workspace_root()
    verdandi, output = resolve_paths(
        args.verdandi_dir, args.output_dir, workspace,
    )
    if args.check:
        return run_check(verdandi, output)
    if args.list:
        return run_list(verdandi)
    return run_all(verdandi, output, workspace)


if __name__ == "__main__":
    sys.exit(main())
