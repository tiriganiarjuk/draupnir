"""Locate Draupnir's own files — the one place the project root is worked out.

CC=1. The root is found from this file's own location, because schemas/ and
tools/ are siblings of the installed package rather than inside it. Each entry
point calls this once and passes the result down.
"""

from pathlib import Path

from draupnir.structure.config.draupnir_paths import DraupnirPaths


def locate_draupnir_paths() -> DraupnirPaths:
    """Resolve the project root (six levels above this file) and the locations beneath it."""
    root = Path(__file__).resolve().parents[5]
    return DraupnirPaths(
        root=str(root),
        input_schema_dir=str(root / "schemas" / "input"),
        config_schema_dir=str(root / "schemas" / "config"),
        codegen_config_file=str(root / "tools" / "codegen_input.toml"),
        structures_dir=str(root / "src" / "draupnir" / "structure"),
    )
