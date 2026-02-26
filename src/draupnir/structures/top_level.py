"""Top-level models: Section, Shallowsection, Schema.

Section holds components (complex containers only). Shallowsection
mixes fields and containers at top level with max 2 containers.
Schema is the root — references sections, shallowsections, or both (at least one).

Ref type aliases defined here:
  ComplexContainerRef — group | array | superarray (for section components)
  ShallowContainerRef — simplearray | array | superarray | group (for shallowsection)
  ShallowFieldConditionalRef — field-level + tuple (shallowsection conditionals)
  SectionOnlyRef — section only (for schema.sections)
  ShallowsectionOnlyRef — shallowsection only (for schema.shallowsections)
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from draupnir.functions.pure.pydantic_validators import ref_from_cache
from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.complex_containers import (
    Array,
    Group,
    Superarray,
)
from draupnir.structures.fields import (
    Atom,
    Element,
    Enum,
    FieldRef,
    Pattern,
    Union_,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Tuple_,
)


# --- Section ---

ComplexContainerRef = Annotated[
    Group | Array | Superarray,
    BeforeValidator(ref_from_cache),
]


class Section(BaseModel):
    """Top-level container — components only, no direct fields."""

    model_config = ConfigDict(frozen=True)

    description: str
    components: dict[str, ComplexContainerRef]


# --- Shallowsection ---

ShallowContainerRef = Annotated[
    Simplearray | Array | Superarray | Group,
    BeforeValidator(ref_from_cache),
]

ShallowFieldConditionalRef = Annotated[
    Pattern | Atom | Enum | Element | Union_ | Tuple_,
    BeforeValidator(ref_from_cache),
]


class ShallowFieldConditionalEntry(BaseModel):
    """Conditional field entry for shallowsection field zones."""

    model_config = ConfigDict(frozen=True)

    ref: ShallowFieldConditionalRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "ShallowFieldConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class ShallowContainers(BaseModel):
    """Container zones for a shallowsection — max 2 total containers."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, ShallowContainerRef] | None = None
    optional: dict[str, ShallowContainerRef] | None = None

    @model_validator(mode="after")
    def max_two_containers(self) -> "ShallowContainers":
        count = 0
        if self.required is not None:
            count += len(self.required)
        if self.optional is not None:
            count += len(self.optional)
        if count > 2:
            msg = f"shallowsection allows max 2 containers, got {count}"
            raise ValueError(msg)
        return self


class Shallowsection(BaseModel):
    """Top-level container with fields and limited containers."""

    model_config = ConfigDict(frozen=True)

    description: str
    required: dict[str, FieldRef] | None = None
    optional: dict[str, FieldRef] | None = None
    conditional: dict[str, ShallowFieldConditionalEntry] | None = None
    containers: ShallowContainers | None = None


# --- Schema ---

SectionOnlyRef = Annotated[Section, BeforeValidator(ref_from_cache)]
ShallowsectionOnlyRef = Annotated[
    Shallowsection, BeforeValidator(ref_from_cache),
]


class Schema(BaseModel):
    """Root schema — references sections, shallowsections, or both."""

    model_config = ConfigDict(frozen=True)

    version: int
    description: str
    required: tuple[str, ...] | None = None
    nullable: tuple[str, ...] | None = None
    sections: dict[str, SectionOnlyRef] | None = None
    shallowsections: dict[str, ShallowsectionOnlyRef] | None = None

    @model_validator(mode="after")
    def at_least_one_section_type(self) -> "Schema":
        has_sections = self.sections is not None
        has_shallow = self.shallowsections is not None
        if not has_sections and not has_shallow:
            msg = "at least one of sections/shallowsections must be set"
            raise ValueError(msg)
        return self
