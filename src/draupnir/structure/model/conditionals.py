"""Conditional presence predicates for Verdandi containers.

ConditionalWhen models the predicate in only_when/always_when/not_when
blocks. Each predicate targets a field path and matches either a single
value (equals), multiple values (in), or property presence (exists).
"""

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
            error_message ="exactly one of 'equals', 'in', or 'exists' must be set"
            raise ValueError(error_message)
        if self.exists is not None and self.exists is not True:
            error_message ="'exists' must be true (use not_when for the inverse)"
            raise ValueError(error_message)
        return self
