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

ShallowsectionFields parallels GroupFields — wraps required/optional/conditional
field zones under a fields: key.
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


class SectionContainerConditionalEntry(BaseModel):
    """Conditional container entry for section container zones."""

    model_config = ConfigDict(frozen=True)

    ref: ComplexContainerRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "SectionContainerConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class SectionContainers(BaseModel):
    """Container zones for a section — required/optional/conditional."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, ComplexContainerRef] | None = None
    optional: dict[str, ComplexContainerRef] | None = None
    conditional: dict[str, SectionContainerConditionalEntry] | None = None


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


class ShallowsectionFields(BaseModel):
    """Field zones for a shallowsection — required, optional, conditional."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, FieldItemRef] | None = None
    optional: dict[str, FieldItemRef] | None = None
    conditional: dict[str, ShallowFieldConditionalEntry] | None = None


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
    fields: ShallowsectionFields | None = None
    containers: ShallowContainers | None = None


# --- Schema ---

SectionOnlyRef = Annotated[Section, BeforeValidator(ref_from_cache)]
ShallowsectionOnlyRef = Annotated[
    Shallowsection, BeforeValidator(ref_from_cache),
]


class SchemaSectionConditionalEntry(BaseModel):
    """Conditional section entry for schema section zones."""

    model_config = ConfigDict(frozen=True)

    ref: SectionOnlyRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "SchemaSectionConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class SchemaShallowConditionalEntry(BaseModel):
    """Conditional shallowsection entry for schema shallowsection zones."""

    model_config = ConfigDict(frozen=True)

    ref: ShallowsectionOnlyRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "SchemaShallowConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class SchemaSections(BaseModel):
    """Zone container for schema sections: key."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, SectionOnlyRef] | None = None
    optional: dict[str, SectionOnlyRef] | None = None
    conditional: dict[str, SchemaSectionConditionalEntry] | None = None


class SchemaShallowsections(BaseModel):
    """Zone container for schema shallowsections: key."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, ShallowsectionOnlyRef] | None = None
    optional: dict[str, ShallowsectionOnlyRef] | None = None
    conditional: dict[str, SchemaShallowConditionalEntry] | None = None


class Schema(BaseModel):
    """Root schema — references sections or shallowsections via zones."""

    model_config = ConfigDict(frozen=True)

    title: str
    version: int
    description: str
    sections: SchemaSections | None = None
    shallowsections: SchemaShallowsections | None = None

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
