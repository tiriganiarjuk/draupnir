"""Conditional presence predicates for Verdandi containers.

ConditionalWhen models the predicate in only_when/always_when/not_when
blocks. Each predicate targets a field path and matches either a single
value (equals), multiple values (in), or property presence (exists).

ConditionalEntry is the structural type shared by all conditional entry
models across tiers (SimplegroupConditionalEntry, GroupFieldConditionalEntry,
etc). Used by zone collection primitives for polymorphic iteration.
"""

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConditionalWhen(BaseModel):
    """Predicate controlling conditional field presence."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    field: str
    equals: str | int | bool | None = None
    in_: tuple[str | int | bool, ...] | None = Field(None, alias="in")
    exists: bool | None = None

    @model_validator(mode="after")
    def exactly_one_predicate(self) -> "ConditionalWhen":
        count = sum([
            self.equals is not None,
            self.in_ is not None,
            self.exists is not None,
        ])
        if count != 1:
            msg = "exactly one of 'equals', 'in', or 'exists' must be set"
            raise ValueError(msg)
        if self.exists is not None and self.exists is not True:
            msg = "'exists' must be true (use not_when for the inverse)"
            raise ValueError(msg)
        return self


class ConditionalEntry(Protocol):
    """Structural type shared by all conditional entry models."""

    @property
    def ref(self) -> BaseModel: ...

    @property
    def only_when(self) -> ConditionalWhen | None: ...

    @property
    def always_when(self) -> ConditionalWhen | None: ...

    @property
    def not_when(self) -> ConditionalWhen | None: ...
