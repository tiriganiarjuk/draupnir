"""Draupnir CLI — generate JSON Schema from Verdandi YAML.

Default mode is --all (generate everything). Single-schema mode
exists for debugging only.
"""

import sys
from pathlib import Path

from draupnir.functions.impure.cli_arguments import build_parser, find_workspace_root
from draupnir.functions.impure.pipeline import (
    resolve_paths,
    run_all,
    run_check,
    run_fragments,
    run_list,
)


def main() -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()
    workspace = args.workspace or find_workspace_root(
        Path(__file__).resolve().parent,
    )
    needs_workspace = workspace is None and not (args.verdandi_dir and args.output_dir)
    if needs_workspace:
        sys.stderr.write(
            "error: cannot find workspace root (no ancestor has tools/verdandi/)\n"
            "  use --workspace, or provide both --verdandi-dir and --output-dir\n",
        )
        return 1
    verdandi, output = resolve_paths(
        args.verdandi_dir, args.output_dir, workspace, args.project,
    )
    if args.check:
        return run_check(verdandi, output)
    if args.list:
        return run_list(verdandi)
    if args.fragments:
        return run_fragments(verdandi, output, workspace)
    return run_all(verdandi, output, workspace)


if __name__ == "__main__":
    sys.exit(main())
