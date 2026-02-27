"""Simple container models: Tuple_, VerdandiField, Simplearray, Simplegroup.

Simple containers hold field-level models but cannot nest other
containers. Tuple_ is fixed-length, Simplearray is variable-length,
Simplegroup is a flat object with required/optional/conditional zones.

VerdandiField (the semantic membrane) lives here because it needs Tuple_
in its type ref, and containers need VerdandiField in their item refs.
Defining them in the same module avoids circular imports.

Ref type aliases defined here:
  FieldTypeRef — type-tier + tuple (for VerdandiField.type, internal to membrane)
  FieldItemRef — VerdandiField only (containers see ONLY the membrane)
  SimplegroupItemRef — simplearray + VerdandiField (for simplegroup zones)
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from draupnir.functions.pure.pydantic_validators import ref_from_cache
from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.field import ConstraintRule, SemanticBlock
from draupnir.structures.fields import (
    Atom,
    Element,
    Enum,
    FieldRef,
    Pattern,
    Union_,
)


class Tuple_(BaseModel):
    """Fixed-length typed sequence."""

    model_config = ConfigDict(frozen=True)

    title: str
    items: tuple[FieldRef, ...]
    constraint: str | None = None
    description: str


# --- VerdandiField: semantic membrane between type-tier and containers ---

FieldTypeRef = Annotated[
    Atom | Enum | Element | Union_ | Tuple_,
    BeforeValidator(ref_from_cache),
]


class VerdandiField(BaseModel):
    """Semantic membrane: type reference + description + extensions."""

    model_config = ConfigDict(frozen=True)

    title: str
    type: FieldTypeRef
    description: str
    semantic: SemanticBlock | None = None
    constraint: tuple[ConstraintRule, ...] | None = None


# --- Ref aliases that include VerdandiField ---

FieldItemRef = Annotated[
    VerdandiField,
    BeforeValidator(ref_from_cache),
]


class Simplearray(BaseModel):
    """Variable-length array of a single field type."""

    model_config = ConfigDict(frozen=True)

    title: str
    items: FieldItemRef
    description: str


SimplegroupItemRef = Annotated[
    Simplearray | VerdandiField,
    BeforeValidator(ref_from_cache),
]


class SimplegroupConditionalEntry(BaseModel):
    """Conditional field entry for simplegroup zones."""

    model_config = ConfigDict(frozen=True)

    ref: SimplegroupItemRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "SimplegroupConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class Simplegroup(BaseModel):
    """Flat object with field zones — no nested containers."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    required: dict[str, SimplegroupItemRef] | None = None
    optional: dict[str, SimplegroupItemRef] | None = None
    conditional: dict[str, SimplegroupConditionalEntry] | None = None

    @model_validator(mode="after")
    def at_least_one_zone(self) -> "Simplegroup":
        if (
            self.required is None
            and self.optional is None
            and self.conditional is None
        ):
            msg = "at least one of required/optional/conditional must be set"
            raise ValueError(msg)
        return self
