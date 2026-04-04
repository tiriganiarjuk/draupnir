"""Simple container models: VerdandiField, Simplearray, Simplegroup.

Simple containers hold field-level models but cannot nest other
containers. Simplearray is variable-length, Simplegroup is a flat
object with required/optional/conditional zones.

VerdandiField (the semantic membrane) lives here because containers
need VerdandiField in their item refs, and VerdandiField needs the
type-tier models from fields.py.

Tuple_ is imported from fields.py (it is a type-tier model, not a
container).

Ref type aliases defined here:
  FieldTypeRef — type-tier + tuple (for VerdandiField.type, internal to membrane)
  FieldItemRef — VerdandiField only (containers see ONLY the membrane)
  SimplegroupItemRef — simplearray + VerdandiField (for simplegroup zones)

Constraints (exactly_one_condition, at_least_one_zone) are enforced
by the input JSON Schema, not by model validators.
"""

from pydantic import BaseModel, ConfigDict

from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.field import ConstraintRule, SemanticBlock
from draupnir.structure.model.fields import (
    Atom,
    Element,
    Enum,
    Tuple_,
    Union_,
)


# --- VerdandiField: semantic membrane between type-tier and containers ---

type FieldTypeRef = Atom | Enum | Element | Union_ | Tuple_


class VerdandiField(BaseModel):
    """Semantic membrane: type reference + description + extensions."""

    model_config = ConfigDict(frozen=True)

    title: str
    type: FieldTypeRef
    const: str | None = None
    default: str | int | bool | list[str] | None = None
    min_length: int | None = None
    max_length: int | None = None
    description: str
    semantic: SemanticBlock | None = None
    constraint: tuple[ConstraintRule, ...] | None = None


# --- Ref aliases that include VerdandiField ---

type FieldItemRef = VerdandiField


class Simplearray(BaseModel):
    """Variable-length array of a single field type."""

    model_config = ConfigDict(frozen=True)

    title: str
    items: FieldItemRef
    min_items: int | None = None
    max_items: int | None = None
    unique_items: bool | None = None
    description: str


type SimplegroupItemRef = Simplearray | VerdandiField


class SimplegroupConditionalEntry(BaseModel):
    """Conditional field entry for simplegroup zones."""

    model_config = ConfigDict(frozen=True)

    ref: SimplegroupItemRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None


class Simplegroup(BaseModel):
    """Flat object with field zones — no nested containers."""

    model_config = ConfigDict(frozen=True)

    title: str
    description: str
    required: dict[str, SimplegroupItemRef] | None = None
    optional: dict[str, SimplegroupItemRef] | None = None
    conditional: dict[str, SimplegroupConditionalEntry] | None = None
