"""Compile dispatch — builder routing table for schema compilation.

L6 dispatch table mapping Verdandi level names to their schema builder
functions. Each builder takes (model: BaseModel, context: BuildContext)
and returns a built schema node.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.schema_build.assembled import (
    build_group,
    build_section,
    build_shallowsection,
    build_simplegroup,
    build_verdandi_field,
)
from draupnir.logic.transform.schema_build.composed import build_atom
from draupnir.logic.transform.schema_build.primitive import (
    build_enum,
    build_pattern,
    build_simplearray,
)
from draupnir.logic.transform.schema_build.simple import (
    build_array,
    build_element,
    build_tuple,
    build_union,
)
from draupnir.structure.config.build_context import BuildContext

BUILDER_DISPATCH: dict[str, Callable[[BaseModel, BuildContext], BaseModel]] = {
    "pattern": build_pattern,
    "enum": build_enum,
    "atom": build_atom,
    "element": build_element,
    "tuple": build_tuple,
    "union": build_union,
    "field": build_verdandi_field,
    "simplearray": build_simplearray,
    "simplegroup": build_simplegroup,
    "array": build_array,
    "group": build_group,
    "superarray": build_array,
    "section": build_section,
    "shallowsection": build_shallowsection,
}
