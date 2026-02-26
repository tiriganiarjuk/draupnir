"""Conditional presence predicates for Verdandi containers.

ConditionalWhen models the predicate in only_when/always_when/not_when
blocks. Each predicate targets a field path and matches either a single
value (equals) or multiple values (in).
"""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConditionalWhen(BaseModel):
    """Predicate controlling conditional field presence."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    field: str
    equals: str | int | bool | None = None
    in_: tuple[str | int | bool, ...] | None = Field(None, alias="in")

    @model_validator(mode="after")
    def exactly_one_predicate(self) -> "ConditionalWhen":
        has_equals = self.equals is not None
        has_in = self.in_ is not None
        if has_equals == has_in:
            msg = "exactly one of 'equals' or 'in' must be set"
            raise ValueError(msg)
        return self
