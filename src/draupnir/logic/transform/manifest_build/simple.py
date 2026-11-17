"""Manifest build — a project's swept Verdandi files into its manifest.

CC=1-3. The files arrive already sorted from strays (pure/source_files); this
reshapes them and decides nothing.
"""

from draupnir.logic.transform.manifest_build.primitive import manifest_entry
from draupnir.structure.config.verdandi_manifest import SweptFiles, VerdandiManifest


def build_manifest(project: str, files: SweptFiles) -> VerdandiManifest:
    """The manifest of every Verdandi file one project can reference."""
    return VerdandiManifest(
        project=project,
        entries=tuple(manifest_entry(entry) for entry in files.level_files),
    )
