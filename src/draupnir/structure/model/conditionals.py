"""Conditional presence predicates for Verdandi containers.

ConditionalWhen models the predicate in only_when/always_when/not_when
blocks. Each predicate targets a field path and matches either a single
value (equals), multiple values (in), or property presence (exists).

Constraints (exactly one of equals/in/exists, exists must be true)
are enforced by the input JSON Schema, not by model validators.
"""

from pydantic import BaseModel, ConfigDict, Field


class ConditionalWhen(BaseModel):
    """Predicate controlling conditional field presence."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    field: str
    equals: str | int | bool | None = None
    in_: tuple[str | int | bool, ...] | None = Field(None, alias="in")
    exists: bool | None = None
