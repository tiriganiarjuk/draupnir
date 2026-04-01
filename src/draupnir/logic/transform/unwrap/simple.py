"""RootModel unwrapping — transform zone.

CC=1-3. Generated input models wrap every value in RootModel classes.
These helpers normalize the unwrapping so higher-level transform
functions (composed+) can focus on schema construction logic rather
than peeling through wrapper layers.

Only functions whose callers are at composed level or above live here —
simple-level callers keep their unwrap functions local because
same-level cross-module imports are banned.

Parallel functions exist in pure/unwrap/simple.py for the pure zone
because transform and pure cannot import from each other.
"""

from pydantic import BaseModel, RootModel


def unwrap_zone(zone: RootModel | None) -> dict[str, RootModel] | None:
    """Unwrap a RootModel zone wrapper to get the underlying dict or None.

    Generated input models wrap each zone dict (required, optional, conditional)
    in a RootModel. The assembled-level build functions call this before passing
    zones to zone_collect functions that expect plain dicts.
    """
    if zone is None:
        return None
    return zone.root


def unwrap_when_equals(when_inner: BaseModel) -> str | int | bool | None:
    """Extract equals value from a generated ConditionalWhen inner model.

    The inner model's .equals is itself a RootModel wrapping the actual
    comparison value. Returns None if no equals predicate is set.
    """
    return when_inner.equals.root if when_inner.equals else None


def unwrap_when_in_values(
    when_inner: BaseModel,
) -> tuple[str | int | bool, ...] | None:
    """Extract in_ values as tuple from a generated ConditionalWhen inner model.

    in_ holds a list of allowed values. Converted to tuple for immutability
    in the ConditionalWhen dataclass. Returns None if no in_ predicate is set.
    """
    values_list = when_inner.in_.root if when_inner.in_ else None
    return tuple(values_list) if values_list else None
