"""Top-level models: Section, Shallowsection, Schema.

Section holds containers (complex containers only). Shallowsection
mixes fields and containers at top level with max 2 containers.
Schema is the root — references sections, shallowsections, or both (at least one).

Ref type aliases defined here:
  ComplexContainerRef — group | array | superarray (for section containers)
  ShallowContainerRef — simplearray | array | superarray | group (for shallowsection)
  ShallowFieldConditionalRef — VerdandiField only (shallowsection conditionals)
  SectionOnlyRef — section only (for schema.sections)
  ShallowsectionOnlyRef — shallowsection only (for schema.shallowsections)
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from draupnir.functions.impure.pydantic_validators import ref_from_cache
from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.complex_containers import (
    Array,
    Group,
    Superarray,
)
from draupnir.structures.simple_containers import (
    FieldItemRef,
    Simplearray,
    VerdandiField,
)


# --- Section ---

ComplexContainerRef = Annotated[
    Group | Array | Superarray,
    BeforeValidator(ref_from_cache),
]


class SectionContainers(BaseModel):
    """Container zones for a section — required/optional."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, ComplexContainerRef] | None = None
    optional: dict[str, ComplexContainerRef] | None = None


class Section(BaseModel):
    """Top-level container — containers only, no direct fields."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    containers: SectionContainers


# --- Shallowsection ---

ShallowContainerRef = Annotated[
    Simplearray | Array | Superarray | Group,
    BeforeValidator(ref_from_cache),
]

ShallowFieldConditionalRef = Annotated[
    VerdandiField,
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

    title: str
    description: str
    required: dict[str, FieldItemRef] | None = None
    optional: dict[str, FieldItemRef] | None = None
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

    title: str
    version: int
    description: str
    required: tuple[str, ...] | None = None
    nullable: tuple[str, ...] | None = None
    sections: dict[str, SectionOnlyRef] | None = None
    shallowsections: dict[str, ShallowsectionOnlyRef] | None = None

    @model_validator(mode="after")
    def exactly_one_section_type(self) -> "Schema":
        has_sections = self.sections is not None
        has_shallow = self.shallowsections is not None
        if not has_sections and not has_shallow:
            msg = "exactly one of sections/shallowsections must be set, got neither"
            raise ValueError(msg)
        if has_sections and has_shallow:
            msg = "sections and shallowsections are mutually exclusive, got both"
            raise ValueError(msg)
        return self
