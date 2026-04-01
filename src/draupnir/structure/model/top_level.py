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

Constraints (exactly_one_condition, max_three_containers, exactly_one_section_type)
are enforced by the input JSON Schema, not by model validators.
"""

from pydantic import BaseModel, ConfigDict

from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.complex_containers import (
    Array,
    Group,
    Superarray,
)
from draupnir.structure.model.simple_containers import (
    FieldItemRef,
    Simplearray,
    Simplegroup,
    VerdandiField,
)


# --- Section ---

type ComplexContainerRef = Group | Array | Superarray


class SectionContainerConditionalEntry(BaseModel):
    """Conditional container entry for section container zones."""

    model_config = ConfigDict(frozen=True)

    ref: ComplexContainerRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None


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

type ShallowContainerRef = Simplegroup | Simplearray | Array | Superarray | Group

type ShallowFieldConditionalRef = VerdandiField


class ShallowFieldConditionalEntry(BaseModel):
    """Conditional field entry for shallowsection field zones."""

    model_config = ConfigDict(frozen=True)

    ref: ShallowFieldConditionalRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None


class ShallowsectionFields(BaseModel):
    """Field zones for a shallowsection — required, optional, conditional."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, FieldItemRef] | None = None
    optional: dict[str, FieldItemRef] | None = None
    conditional: dict[str, ShallowFieldConditionalEntry] | None = None


class ShallowContainerConditionalEntry(BaseModel):
    """Conditional container entry for shallowsection container zones."""

    model_config = ConfigDict(frozen=True)

    ref: ShallowContainerRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None


class ShallowContainers(BaseModel):
    """Container zones for a shallowsection — max 3 total containers."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, ShallowContainerRef] | None = None
    optional: dict[str, ShallowContainerRef] | None = None
    conditional: dict[str, ShallowContainerConditionalEntry] | None = None


class Shallowsection(BaseModel):
    """Top-level container with fields and limited containers."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    fields: ShallowsectionFields | None = None
    containers: ShallowContainers | None = None


# --- Schema ---

type SectionOnlyRef = Section
type ShallowsectionOnlyRef = Shallowsection


class SchemaSectionConditionalEntry(BaseModel):
    """Conditional section entry for schema section zones."""

    model_config = ConfigDict(frozen=True)

    ref: SectionOnlyRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None


class SchemaShallowConditionalEntry(BaseModel):
    """Conditional shallowsection entry for schema shallowsection zones."""

    model_config = ConfigDict(frozen=True)

    ref: ShallowsectionOnlyRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None


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
