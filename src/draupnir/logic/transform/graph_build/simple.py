"""Graph build simple — ref identification and field extraction.

CC=1-3. Composes primitives into ref pattern detection.
Extracts inspectable children from BaseModel fields.
"""

from pydantic import BaseModel

from draupnir.logic.transform.graph_build.primitive import is_known_level, ref_prefix


def is_cache_ref(value: str) -> bool:
    """Check if a string matches the level/name cache ref pattern."""
    return "/" in value and is_known_level(ref_prefix(value))


def base_model_children(model: BaseModel) -> list[BaseModel | str]:
    """Return non-None field values that are BaseModel or str instances."""
    return [value for _name, value in model if isinstance(value, (BaseModel, str))]
