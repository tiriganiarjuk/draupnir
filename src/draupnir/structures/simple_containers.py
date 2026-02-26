"""Simple container models: Tuple_, Simplearray, Simplegroup.

Simple containers hold field-level models but cannot nest other
containers. Tuple_ is fixed-length, Simplearray is variable-length,
Simplegroup is a flat object with required/optional/conditional zones.

Ref type aliases defined here:
  SimplegroupItemRef — field-level + tuple + simplearray (for simplegroup zones)
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from draupnir.functions.pure.pydantic_validators import ref_from_cache
from draupnir.structures.conditionals import ConditionalWhen
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

    items: tuple[FieldRef, ...]
    constraint: str | None = None
    description: str


class Simplearray(BaseModel):
    """Variable-length array of a single field type."""

    model_config = ConfigDict(frozen=True)

    items: FieldRef
    description: str


SimplegroupItemRef = Annotated[
    Pattern | Atom | Enum | Element | Union_ | Tuple_ | Simplearray,
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
