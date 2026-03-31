"""Field-level Verdandi models: Pattern, Atom, Enum, Element, Tuple_, Union_.

These are the lowest composition levels. Each model is frozen. String
refs are resolved to model instances by the loader's ref_resolve
transform before validation.

Type aliases (PatternRef, AtomOrEnumRef, UnionMemberRef, FieldRef)
are imported by higher-level structure modules.

Tuple_ lives here (not in simple_containers) because it is a type-tier
model — fixed-length typed sequence, not a container. Unions may reference
tuples, so Tuple_ must be defined before Union_ in the same module.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Pattern(BaseModel):
    """Raw regex pattern — the lowest building block."""

    model_config = ConfigDict(frozen=True)

    title: str
    regex: str
    description: str


type PatternRef = Pattern


class Atom(BaseModel):
    """Constrained base type: string, integer, or boolean."""

    model_config = ConfigDict(frozen=True)

    title: str
    type: Literal["string", "integer", "boolean"]
    pattern: PatternRef | None = None
    excludes: tuple[PatternRef, ...] | None = None
    min_length: int | None = None
    description: str


class Enum(BaseModel):
    """Enumerated allowed values."""

    model_config = ConfigDict(frozen=True)

    title: str
    values: tuple[str | int | bool, ...]
    description: str


type AtomOrEnumRef = Atom | Enum


class Element(BaseModel):
    """Atom or Enum with a runtime format contract."""

    model_config = ConfigDict(frozen=True)

    title: str
    inherits: AtomOrEnumRef
    format: str | None = None
    required: Literal["mandatory"] | None = None
    description: str


class Tuple_(BaseModel):
    """Fixed-length typed sequence — type composition, not a container.

    Items reference type-tier models (atom, enum, element, union).
    Defined before Union_ so unions can reference tuples.
    """

    model_config = ConfigDict(frozen=True)

    title: str
    items: tuple["FieldRef", ...]
    constraint: str | None = None
    description: str


# Union members: atom/enum/element/tuple — not patterns, not unions.
type UnionMemberRef = Atom | Enum | Element | Tuple_


class Union_(BaseModel):
    """OneOf composition of field-level models."""

    model_config = ConfigDict(frozen=True)

    title: str
    union: tuple[UnionMemberRef, ...]
    description: str


# FieldRef includes all 6 field types. Defined after Union_ to avoid
# forward references. Used by simple_containers, complex_containers,
# and top_level modules.
type FieldRef = Pattern | Atom | Enum | Element | Tuple_ | Union_

# Resolve forward reference in Tuple_.items now that FieldRef exists.
Tuple_.model_rebuild()
