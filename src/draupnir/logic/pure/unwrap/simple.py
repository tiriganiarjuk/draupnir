"""RootModel unwrapping — pure zone.

CC=1-3. Generated input models wrap every value in RootModel classes.
These helpers normalize the unwrapping so higher-level pure functions
can focus on graph analysis and cross-section logic rather than peeling
through wrapper layers.

Parallel functions exist in transform/unwrap/simple.py for the transform
zone because transform and pure cannot import from each other. The
duplication is the cost of zone isolation.
"""

from pydantic import BaseModel, RootModel


def unwrap_zone_dict(wrapper: RootModel | None) -> dict[str, BaseModel] | None:
    """Access .root on a zone RootModel and verify it's a dict.

    Generated zone fields are RootModel[dict[str, RefType] | None] —
    .root is either a dict mapping field names to ref wrappers, or None
    when the zone is absent in the source YAML. Returns the dict for
    iteration, or None to signal "skip this zone."
    """
    if wrapper is None:
        return None
    return wrapper.root if isinstance(wrapper.root, dict) else None


def unwrap_ref_value(wrapper: RootModel | BaseModel | str | None) -> str | None:
    """Access .root on a ref RootModel to get the cache key string.

    Generated ref fields are RootModel[str] — .root is the cache key
    (e.g., "atom/boolean"). Falls through gracefully if the wrapper is
    already a plain string or if the inner value isn't a string.
    """
    ref_value = wrapper.root if isinstance(wrapper, RootModel) else wrapper
    return ref_value if isinstance(ref_value, str) else None


def unwrap_when_field(when_wrapper: RootModel | BaseModel | None) -> str | None:
    """Peel a raw edge when-condition down to the field name it names.

    Graph edges carry when-conditions in generated form — RootModel wrapping
    an inner model whose .field is itself RootModel[str]. This takes both
    layers off and returns the bare name, or None when there is no condition
    or the shape is not what we expect.
    """
    inner = when_wrapper.root if isinstance(when_wrapper, RootModel) else when_wrapper
    return unwrap_ref_value(getattr(inner, "field", None))


def unwrap_when_equals(when_inner: BaseModel) -> str | int | bool | None:
    """Access .equals.root on the generated ConditionalWhen inner model.

    The inner model's .equals field is RootModel[str | int | bool | None].
    Returns None both when .equals is absent and when its value is None.
    """
    return when_inner.equals.root if when_inner.equals else None


def unwrap_when_in_values(
    when_inner: BaseModel,
) -> tuple[str | int | bool, ...] | None:
    """Access .in_.root and convert the list to a tuple for frozen model use.

    The inner model's .in_ field is RootModel[list[...] | None]. Tuple
    conversion is required because ConditionalWhen.in_ is typed as tuple
    (frozen Pydantic models need immutable collections).
    """
    values_list = when_inner.in_.root if when_inner.in_ else None
    return tuple(values_list) if values_list else None
