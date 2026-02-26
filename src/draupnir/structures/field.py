"""Field-level Verdandi model: the semantic membrane between types and containers.

A Field wraps a type-tier reference (atom, enum, element, union, tuple) with
a human-readable description and optional semantic/constraint extension blocks.
Fields sit between the type tier and the container tier in load order.
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field as PydanticField

from draupnir.functions.pure.pydantic_validators import ref_from_cache
from draupnir.structures.fields import Atom, Element, Enum, Union_
from draupnir.structures.simple_containers import Tuple_


FieldTypeRef = Annotated[
    Atom | Enum | Element | Union_ | Tuple_,
    BeforeValidator(ref_from_cache),
]


class SemanticBlock(BaseModel):
    """Semantic intent and validation guidance for a field."""

    model_config = ConfigDict(frozen=True)

    intent: str | None = None
    checks: tuple[str, ...] | None = None
    anti_patterns: tuple[str, ...] | None = None
    severity: str | None = None


class ConstraintRule(BaseModel):
    """Cross-field validation rule carried by a field."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rule: str
    severity: str
    reason: str
    field: str | None = None
    order: str | None = None
    values: tuple[str, ...] | None = PydanticField(default=None, alias="in")


class VerdandiField(BaseModel):
    """Semantic membrane: type reference + description + extensions."""

    model_config = ConfigDict(frozen=True)

    type: FieldTypeRef
    description: str
    semantic: SemanticBlock | None = None
    constraint: tuple[ConstraintRule, ...] | None = None
