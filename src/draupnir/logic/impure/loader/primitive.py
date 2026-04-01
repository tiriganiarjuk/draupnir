"""Loader primitives — filesystem path construction.

CC=1 helpers. Build paths for Verdandi YAML files and the input schema
directory. The schema directory path uses __file__ traversal rather than
package resources because the schemas/ directory is a sibling of the
installed package, not inside it.
"""

from pathlib import Path


def level_file_path(root: Path, level_name: str, name: str) -> Path:
    """Build the filesystem path for a Verdandi YAML file.

    Verdandi organizes files by level: root/level_name/name.yaml.
    Level names match the Level enum (pattern, atom, element, etc.).
    """
    return root / level_name / f"{name}.yaml"


def schema_dir_path() -> str:
    """Return the path to the input schema directory.

    Traverses up from this file to the project root (6 parents:
    this file → loader → impure → logic → draupnir → src → project root),
    then into schemas/input/. These schemas are used by the Rust PyO3 gate
    for YAML validation before Python model parsing.
    """
    return str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent / "schemas" / "input")
