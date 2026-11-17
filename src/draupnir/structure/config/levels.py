"""Verdandi composition levels in dependency order.

Declaration order IS the load order. Member values are the input models
generated from schemas/input/{level}.schema.json — the authored source of what
a Verdandi file at each level may contain. Iterating yields levels bottom-up:
lower tiers first, so every reference a file names is in the cache when that
file validates.
"""

import enum

from draupnir.structure.gen.input.array import Array
from draupnir.structure.gen.input.atom import Atom
from draupnir.structure.gen.input.element import Element
from draupnir.structure.gen.input.enum import Enum
from draupnir.structure.gen.input.field import VerdandiField
from draupnir.structure.gen.input.group import Group
from draupnir.structure.gen.input.pattern import Pattern
from draupnir.structure.gen.input.schema import Schema
from draupnir.structure.gen.input.section import Section
from draupnir.structure.gen.input.shallowsection import Shallowsection
from draupnir.structure.gen.input.simplearray import Simplearray
from draupnir.structure.gen.input.simplegroup import Simplegroup
from draupnir.structure.gen.input.superarray import Superarray
from draupnir.structure.gen.input.tuple import Tuple
from draupnir.structure.gen.input.union import Union


class Level(enum.Enum):
    """Verdandi composition levels in dependency order.

    Declaration order is the load order. Use Level[name] for lookup,
    level.value for the generated input model, and iteration for ordered
    traversal.
    """

    pattern = Pattern
    enum = Enum
    atom = Atom
    element = Element
    tuple = Tuple
    union = Union
    field = VerdandiField
    simplearray = Simplearray
    simplegroup = Simplegroup
    array = Array
    group = Group
    superarray = Superarray
    section = Section
    shallowsection = Shallowsection
    schema = Schema
