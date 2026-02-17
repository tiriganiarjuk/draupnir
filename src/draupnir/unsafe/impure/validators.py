"""Validate raw YAML data and convert to type-safe structures.

UNSAFE/IMPURE: Raw dicts may have invalid structure.
May raise ValueError (error path).

This module secures the boundary between dirty YAML and clean internal types.
Because models match YAML shapes exactly, validation is mostly Pydantic's
model_validate with source-path context on errors.
"""

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSchema,
    RawSection,
)


def _validation_error(source: Path | str, pydantic_error: ValidationError) -> ValueError:
    """Format a Pydantic ValidationError with source path context."""
    return ValueError(f"{source}: {pydantic_error}")


def validate_primitive(data: dict[str, Any], source: Path | str = "") -> RawPrimitive:
    """Validate a raw YAML dict as a primitive field type."""
    try:
        return RawPrimitive.model_validate(data)
    except ValidationError as e:
        raise _validation_error(source, e) from e


def validate_composed(data: dict[str, Any], source: Path | str = "") -> RawComposed:
    """Validate a raw YAML dict as a composed field."""
    try:
        return RawComposed.model_validate(data)
    except ValidationError as e:
        raise _validation_error(source, e) from e


def validate_group(data: dict[str, Any], source: Path | str = "") -> RawGroup:
    """Validate a raw YAML dict as a group (or supergroup)."""
    try:
        return RawGroup.model_validate(data)
    except ValidationError as e:
        raise _validation_error(source, e) from e


def validate_array(data: dict[str, Any], source: Path | str = "") -> RawArray:
    """Validate a raw YAML dict as an array (or superarray)."""
    try:
        return RawArray.model_validate(data)
    except ValidationError as e:
        raise _validation_error(source, e) from e


def validate_section(data: dict[str, Any], source: Path | str = "") -> RawSection:
    """Validate a raw YAML dict as a section."""
    try:
        return RawSection.model_validate(data)
    except ValidationError as e:
        raise _validation_error(source, e) from e


def validate_schema(data: dict[str, Any], source: Path | str = "") -> RawSchema:
    """Validate a raw YAML dict as a schema root definition."""
    try:
        return RawSchema.model_validate(data)
    except ValidationError as e:
        raise _validation_error(source, e) from e
