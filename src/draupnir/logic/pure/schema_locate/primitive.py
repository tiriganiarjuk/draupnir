"""Locate the schemas Draupnir validates its own files against.

CC=1. Each location pairs a name from DraupnirSchemas with the directory
DraupnirPaths gives for it — the way the Nornir readers and writers take a schema.
"""

from pathlib import PurePath

from draupnir.structure.config.draupnir_paths import DraupnirPaths
from draupnir.structure.config.draupnir_schemas import DraupnirSchemas
from draupnir.structure.config.schema_location import SchemaLocation


def schema_file_path(location: SchemaLocation) -> str:
    """The file a schema location names: {directory}/{name}.schema.json."""
    return str(PurePath(location.directory) / f"{location.name}.schema.json")


def input_schema_location(paths: DraupnirPaths, level_name: str) -> SchemaLocation:
    """The input schema a Verdandi level's files are read against."""
    return SchemaLocation(name=level_name, directory=paths.input_schema_dir)


def json_schema_document_schema(paths: DraupnirPaths) -> SchemaLocation:
    """The schema every schema file is written and read against: a JSON Schema document."""
    return SchemaLocation(
        name=DraupnirSchemas().json_schema_document,
        directory=paths.config_schema_dir,
    )


def verdandi_manifest_schema(paths: DraupnirPaths) -> SchemaLocation:
    """The schema a project's swept manifest is written and read against."""
    return SchemaLocation(
        name=DraupnirSchemas().verdandi_manifest,
        directory=paths.config_schema_dir,
    )
