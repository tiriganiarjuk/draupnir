"""Verdandi composition levels in dependency order.

Declaration order IS the load order. Member values are the Pydantic
model classes. Iterating yields levels bottom-up: lower tiers first,
guaranteeing that refs are in cache when higher tiers validate.

This is pure architectural data — the single source of truth for
level ordering and level-to-model mapping.
"""

import enum

from draupnir.structure.model.complex_containers import (
    Array,
    Group,
    Superarray,
)
from draupnir.structure.model.simple_containers import VerdandiField
from draupnir.structure.model.fields import (
    Atom,
    Element,
)
from draupnir.structure.model.fields import Enum as VerdandiEnum
from draupnir.structure.model.fields import (
    Pattern,
    Tuple_,
    Union_,
)
from draupnir.structure.model.simple_containers import (
    Simplearray,
    Simplegroup,
)
from draupnir.structure.model.top_level import (
    Schema,
    Section,
    Shallowsection,
)


class Level(enum.Enum):
    """Verdandi composition levels in dependency order.

    Declaration order is the load order. Member values are the Pydantic
    model classes for that level. Use Level[name] for lookup, level.value
    for the model class, and iteration for ordered traversal.
    """

    pattern = Pattern
    enum = VerdandiEnum
    atom = Atom
    element = Element
    tuple = Tuple_
    union = Union_
    field = VerdandiField
    simplearray = Simplearray
    simplegroup = Simplegroup
    array = Array
    group = Group
    superarray = Superarray
    section = Section
    shallowsection = Shallowsection
    schema = Schema
