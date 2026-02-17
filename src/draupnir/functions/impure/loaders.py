"""Load YAML files into typed Pydantic models.

IMPURE: File system reads. But NOT unsafe — the data structure is
known at every call site. The caller knows which type to expect,
and Pydantic validates immediately. No untyped data escapes.

Each loader reads a YAML file and returns a validated frozen model.
ValidationError is caught and re-raised with source path context.
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSchema,
    RawSection,
    SchemaLoaders,
)


def format_validation_error(
    source: Path,
    pydantic_error: ValidationError,
) -> ValueError:
    """Format a Pydantic ValidationError with source path context."""
    return ValueError(f"{source}: {pydantic_error}")


def load_primitive(path: Path) -> RawPrimitive:
    """Load a YAML file as a validated RawPrimitive."""
    data = yaml.safe_load(path.read_text())
    try:
        return RawPrimitive.model_validate(data)
    except ValidationError as e:
        raise format_validation_error(path, e) from e


def load_composed(path: Path) -> RawComposed:
    """Load a YAML file as a validated RawComposed."""
    data = yaml.safe_load(path.read_text())
    try:
        return RawComposed.model_validate(data)
    except ValidationError as e:
        raise format_validation_error(path, e) from e


def load_group(path: Path) -> RawGroup:
    """Load a YAML file as a validated RawGroup."""
    data = yaml.safe_load(path.read_text())
    try:
        return RawGroup.model_validate(data)
    except ValidationError as e:
        raise format_validation_error(path, e) from e


def load_array(path: Path) -> RawArray:
    """Load a YAML file as a validated RawArray."""
    data = yaml.safe_load(path.read_text())
    try:
        return RawArray.model_validate(data)
    except ValidationError as e:
        raise format_validation_error(path, e) from e


def load_section(path: Path) -> RawSection:
    """Load a YAML file as a validated RawSection."""
    data = yaml.safe_load(path.read_text())
    try:
        return RawSection.model_validate(data)
    except ValidationError as e:
        raise format_validation_error(path, e) from e


def load_schema(path: Path) -> RawSchema:
    """Load a YAML file as a validated RawSchema."""
    data = yaml.safe_load(path.read_text())
    try:
        return RawSchema.model_validate(data)
    except ValidationError as e:
        raise format_validation_error(path, e) from e


def load_all_primitives(directory: Path) -> list[RawPrimitive]:
    """Load all .yaml files in a directory as RawPrimitives.

    Returns an empty list if the directory does not exist.
    """
    if not directory.exists():
        return []
    return [load_primitive(p) for p in sorted(directory.glob("*.yaml"))]


def make_schema_loaders(root: Path) -> SchemaLoaders:
    """Build SchemaLoaders that resolve paths relative to root.

    Each loader joins root + relative PurePosixPath, converts to
    a real Path, reads the YAML, and validates into the typed model.
    """
    return SchemaLoaders(
        composed=lambda p: load_composed(root / p),
        group=lambda p: load_group(root / p),
        array=lambda p: load_array(root / p),
        section=lambda p: load_section(root / p),
    )
