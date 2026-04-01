"""Input model levels — generated input model classes by level name.

Parallels the Level enum but maps to generated input models with string
ref fields. Used by the loader to select the correct model for
model_validate_json after the gate returns JSON.
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


class InputLevel(enum.Enum):
    """Generated input model classes by level name.

    Declaration order matches Level enum. Member values are the generated
    Pydantic model classes with string ref fields. Use InputLevel[name].value
    to get the model class for a given level name.
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
