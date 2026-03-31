"""Type-to-builder routing table for simple-level schema types.

Maps Verdandi model types to primitive/simple-level schema builders.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.schema_build.primitive import build_simplearray
from draupnir.logic.transform.schema_build.simple import (
    build_array,
    build_superarray,
    build_tuple,
    build_union,
)
from draupnir.structure.model.complex_containers import Array, Superarray
from draupnir.structure.model.fields import Tuple_, Union_
from draupnir.structure.model.simple_containers import Simplearray

dispatch: dict[type[BaseModel], Callable] = {
    Tuple_: build_tuple,
    Simplearray: build_simplearray,
    Union_: build_union,
    Array: build_array,
    Superarray: build_superarray,
}
