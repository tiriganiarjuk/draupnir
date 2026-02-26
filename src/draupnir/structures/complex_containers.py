"""Complex container models: Array, Group, Superarray.

Complex containers can nest other containers. Array holds simplegroups
(or oneOf simplegroups). Group has fields + containers sections with
per-context conditional entries. Superarray holds groups or simplegroups
(or oneOf mix).

Ref type aliases defined here:
  SimplegroupRef — single simplegroup ref (for array items, oneOf members)
  GroupContainerRef — tuple | simplearray | simplegroup | array (group containers)
  GroupFieldConditionalRef — field-level + tuple (group field conditionals)
  GroupOrSimplegroupRef — group | simplegroup (for superarray items)
"""

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from draupnir.functions.pure.pydantic_validators import ref_from_cache
from draupnir.structures.conditionals import ConditionalWhen
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
    Simplegroup,
    Tuple_,
)


# --- Array models ---

SimplegroupRef = Annotated[Simplegroup, BeforeValidator(ref_from_cache)]


class ArrayOneOf(BaseModel):
    """OneOf composition for array items — multiple simplegroup options."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[SimplegroupRef, ...] = Field(alias="oneOf")
    description: str | None = None


class Array(BaseModel):
    """Variable-length array of simplegroup items.

    Items is either a single simplegroup ref (string) or a oneOf
    composition ({oneOf: [...]}). Pydantic union matching handles both:
    string → SimplegroupRef, dict → ArrayOneOf.
    """

    model_config = ConfigDict(frozen=True)

    items: SimplegroupRef | ArrayOneOf
    description: str


# --- Group models ---

GroupContainerRef = Annotated[
    Tuple_ | Simplearray | Simplegroup | Array,
    BeforeValidator(ref_from_cache),
]

GroupFieldConditionalRef = Annotated[
    Pattern | Atom | Enum | Element | Union_ | Tuple_,
    BeforeValidator(ref_from_cache),
]


class GroupFieldConditionalEntry(BaseModel):
    """Conditional field entry for group field zones."""

    model_config = ConfigDict(frozen=True)

    ref: GroupFieldConditionalRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "GroupFieldConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class GroupContainerConditionalEntry(BaseModel):
    """Conditional container entry for group container zones."""

    model_config = ConfigDict(frozen=True)

    ref: GroupContainerRef
    only_when: ConditionalWhen | None = None
    always_when: ConditionalWhen | None = None
    not_when: ConditionalWhen | None = None

    @model_validator(mode="after")
    def exactly_one_condition(self) -> "GroupContainerConditionalEntry":
        conditions = (
            self.only_when is not None,
            self.always_when is not None,
            self.not_when is not None,
        )
        if sum(conditions) != 1:
            msg = "exactly one of only_when/always_when/not_when required"
            raise ValueError(msg)
        return self


class GroupFields(BaseModel):
    """Field zones for a group — required, optional, conditional."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, FieldRef] | None = None
    optional: dict[str, FieldRef] | None = None
    conditional: dict[str, GroupFieldConditionalEntry] | None = None


class GroupContainers(BaseModel):
    """Container zones for a group — required, optional, conditional."""

    model_config = ConfigDict(frozen=True)

    required: dict[str, GroupContainerRef] | None = None
    optional: dict[str, GroupContainerRef] | None = None
    conditional: dict[str, GroupContainerConditionalEntry] | None = None


class Group(BaseModel):
    """Object with fields and/or containers — nesting allowed."""

    model_config = ConfigDict(frozen=True)

    description: str
    fields: GroupFields | None = None
    containers: GroupContainers | None = None

    @model_validator(mode="after")
    def at_least_one_section(self) -> "Group":
        if self.fields is None and self.containers is None:
            msg = "at least one of fields/containers must be set"
            raise ValueError(msg)
        return self


# --- Superarray models ---

GroupOrSimplegroupRef = Annotated[
    Group | Simplegroup,
    BeforeValidator(ref_from_cache),
]


class SuperarrayOneOf(BaseModel):
    """OneOf composition for superarray items — group/simplegroup options."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[GroupOrSimplegroupRef, ...] = Field(alias="oneOf")
    description: str | None = None


class Superarray(BaseModel):
    """Variable-length array of group or simplegroup items.

    Items is either a single group/simplegroup ref (string) or a oneOf
    composition ({oneOf: [...]}). Pydantic union matching handles both.
    """

    model_config = ConfigDict(frozen=True)

    items: GroupOrSimplegroupRef | SuperarrayOneOf
    description: str
