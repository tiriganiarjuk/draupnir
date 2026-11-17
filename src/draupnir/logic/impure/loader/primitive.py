"""Loader primitives — Verdandi file path construction.

CC=1. Verdandi organizes files by level: root/level_name/name.yaml. Joining
names needs no disk, so the path is a PurePath.
"""

from pathlib import PurePath


def level_file_path(root: PurePath, level_name: str, name: str) -> PurePath:
    """Build the path of a Verdandi YAML file.

    Level names match the Level enum (pattern, atom, element, etc.).
    """
    return root / level_name / f"{name}.yaml"
