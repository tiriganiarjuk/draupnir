"""Verdandi manifest — every file one project can reference, by level and name.

The sweep writes one manifest per project; the loader reads files by its names,
and the input-schema export turns each level's names into the set a reference
to that level may hold. schemas/config/verdandi-manifest.schema.json is
exported from this model.

LevelName is derived from Level, the one home of the level names and their
order, so the manifest's level set cannot drift from the levels Draupnir loads.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from draupnir.structure.config.levels import Level
from draupnir.structure.gen.tools.directory_listing import Entry

LevelName = StrEnum("LevelName", [level.name for level in Level])


class VerdandiLayout(BaseModel):
    """How a Verdandi source tree lays out its files: {level}/{name}{file_suffix}."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    file_suffix: str = ".yaml"


class SweptFiles(BaseModel):
    """A project's source listing, sorted: the Verdandi files, and every file that is not one.

    A Verdandi file sits at {level}/{name}.yaml under a known level. A stray is any
    other file; a sweep that finds one refuses, naming every stray.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    level_files: tuple[Entry, ...]
    strays: tuple[Entry, ...]


class ManifestEntry(BaseModel):
    """One Verdandi file: its level directory and its file name without .yaml."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: LevelName
    name: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")]


class VerdandiManifest(BaseModel):
    """Every Verdandi file one project can reference, as swept from its source and core's.

    A file is a reference target only once a sweep has listed it here. The
    type-tier levels are listed from core.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    entries: Annotated[tuple[ManifestEntry, ...], Field(json_schema_extra={"uniqueItems": True})]
