"""Shared ref conversion for Verdandi YAML references.

Every Verdandi YAML file uses string references like "atom/kebab_string"
to point at other files. The ref_from_cache BeforeValidator converts
these strings to actual cached Pydantic models during validation.

The Annotated type aliases (FieldRef, SimplegroupItemRef, etc.) are
defined in each structure module — not here — to avoid circular imports.
Each structure module defines its own alias using the union of types
available at that import level.
"""

from pydantic import BaseModel, ValidationInfo


def ref_from_cache(
    value: str | BaseModel,
    info: ValidationInfo,
) -> BaseModel:
    """Convert a string ref to a cached model, or pass through.

    Used as a Pydantic BeforeValidator on ref fields. When YAML is
    loaded, string refs like "atom/kebab_string" are looked up in
    the cache and replaced with the actual frozen model.

    The cache is guaranteed to contain the referenced model because
    supply-driven loading fills lower levels first.

    Pass-through for models handles test cases where models are
    provided directly instead of string refs.
    """
    if isinstance(value, BaseModel):
        return value
    if not isinstance(value, str):
        msg = f"expected string ref or model, got {type(value).__name__}"
        raise ValueError(msg)
    cache = info.context["cache"]
    if value not in cache:
        msg = f"ref not in cache: {value!r}"
        raise ValueError(msg)
    return cache[value]
