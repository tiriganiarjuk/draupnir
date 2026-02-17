"""CLI entry point for draupnir schema generator.

IMPURE: Argument parsing, process exit codes.
Thin wrapper — parses args, dispatches to command functions.
"""

import argparse
import sys
from pathlib import Path

from draupnir.functions.impure.commands import (
    cmd_check,
    cmd_generate_all,
    cmd_generate_one,
    cmd_list,
    resolve_paths,
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="draupnir",
        description="Generate JSON Schema from toolcompose definitions.",
    )
    parser.add_argument(
        "name", nargs="?", default=None,
        help="Schema name to generate (e.g., agent-definition)",
    )
    parser.add_argument(
        "--all", action="store_true", dest="generate_all",
        help="Generate all schemas",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check for drift without writing (exit 1 if drift)",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_schemas",
        help="List available schema definitions",
    )
    parser.add_argument(
        "--standards-dir", type=Path, default=None,
        help="Override toolcompose root directory",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Override output directory for generated schemas",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parent.parent.parent.parent.parent
    standards_dir, output_dir = resolve_paths(
        args.standards_dir, args.output_dir, workspace,
    )
    if args.list_schemas:
        return cmd_list(standards_dir)
    if args.generate_all:
        if args.check:
            return cmd_check(standards_dir, output_dir)
        return cmd_generate_all(standards_dir, output_dir)
    if args.name:
        return cmd_generate_one(args.name, standards_dir, output_dir)
    parser.print_help()
    return 1
