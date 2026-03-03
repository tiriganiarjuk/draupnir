"""CLI argument definitions and workspace discovery.

Builds the argparse parser for draupnir. Impure because argparse
mutates parser state and find_workspace_root walks the filesystem.
"""

import argparse
from pathlib import Path


def find_workspace_root(start: Path) -> Path:
    """Find the workspace root by walking up from a starting path.

    Identifies the workspace root as the first ancestor containing
    tools/verdandi/. Falls back to the starting path's great-great-grandparent.
    """
    for parent in start.parents:
        if (parent / "tools" / "verdandi").is_dir():
            return parent
    return start.parents[3]


def add_mode_group(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """Add mutually exclusive mode arguments. Returns parser for composition."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--all", action="store_true", default=True,
        help="Generate all schemas (default)",
    )
    group.add_argument(
        "--check", action="store_true",
        help="Check for drift without writing",
    )
    group.add_argument(
        "--list", action="store_true",
        help="List available schemas",
    )
    group.add_argument(
        "--fragments", action="store_true",
        help="Generate include-fragment schemas",
    )
    return parser


def add_path_arguments(
    parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    """Add path override arguments. Returns parser for composition."""
    parser.add_argument(
        "--project", type=str, default=None,
        help="Verdandi project name (e.g. agent-builder). "
        "Reads from verdandi/{project}/source/, "
        "writes to verdandi/{project}/output/.",
    )
    parser.add_argument(
        "--verdandi-dir", type=Path, default=None,
        help="Override Verdandi source directory (overrides --project input)",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=None,
        help="Override output directory (overrides --project output)",
    )
    parser.add_argument(
        "--workspace", type=Path, default=None,
        help="Override workspace root",
    )
    return parser


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="draupnir",
        description="Generate JSON Schema from Verdandi YAML.",
    )
    add_mode_group(parser)
    add_path_arguments(parser)
    return parser
