"""Loader primitives — Verdandi file path construction.

CC=1. Verdandi organizes files by level: root/{level}/{name}{suffix}. Joining
names needs no disk, so the path is a PurePath.
"""

from pathlib import PurePath

from draupnir.structure.config.verdandi_manifest import ManifestEntry, VerdandiLayout


def level_file_path(root: PurePath, entry: ManifestEntry, layout: VerdandiLayout) -> PurePath:
    """The path of the Verdandi file one manifest entry names."""
    return root / entry.level / f"{entry.name}{layout.file_suffix}"
