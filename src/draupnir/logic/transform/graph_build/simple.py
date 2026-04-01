"""Graph build simple — ref identification and field extraction.

CC=1-3. Composes primitives into ref pattern detection.
Extracts inspectable children from BaseModel fields.
Unwraps RootModel wrappers used by generated input models.
"""

import networkx as nx
from pydantic import BaseModel, RootModel

from draupnir.logic.transform.graph_build.primitive import is_known_level, ref_prefix
from draupnir.structure.config.edge_ref import EdgeRef


def is_cache_ref(value: str) -> bool:
    """Check if a string matches the level/name cache ref pattern."""
    return "/" in value and is_known_level(ref_prefix(value))


def base_model_children(model: BaseModel) -> list[BaseModel | str]:
    """Return non-None field values that are BaseModel or str instances."""
    return [value for _name, value in model if isinstance(value, (BaseModel, str))]


def has_zone_fields(model: BaseModel) -> bool:
    """Check if a model has required/optional/conditional zone structure."""
    field_names = {name for name, _ in model}
    return "required" in field_names and "optional" in field_names


def unwrap_zone_dict(wrapper: RootModel | None) -> dict[str, BaseModel] | None:
    """Unwrap a zone RootModel wrapper to its dict, or None if absent.

    Zone dicts in generated input models are RootModel[dict[str, RefType] | None].
    Returns the inner dict, or None if wrapper is missing or wrong type.
    """
    if wrapper is None:
        return None
    return wrapper.root if isinstance(wrapper.root, dict) else None


def edge_ref_to_attrs(edge_ref: EdgeRef) -> dict[str, str | BaseModel]:
    """Convert an EdgeRef to a dict of edge attributes for graph construction.

    Always includes zone and name. Adds only_when/always_when/not_when
    when present on the EdgeRef.
    """
    attrs: dict[str, str | BaseModel] = {"zone": edge_ref.zone, "name": edge_ref.name}
    for when_field in ("only_when", "always_when", "not_when"):
        when_value = getattr(edge_ref, when_field)
        if when_value is not None:
            attrs[when_field] = when_value
    return attrs


def schema_shared_keys(schema_key: str, graph: nx.DiGraph) -> frozenset[str]:
    """Find cache keys shared within a schema's subgraph.

    Returns keys with in-degree >= 2 in the induced subgraph of the
    schema's descendants. These are nodes referenced by 2+ parents
    within a single schema — candidates for per-schema $defs.
    """
    descendants = nx.descendants(graph, schema_key)
    subgraph = graph.subgraph(descendants)
    return frozenset(
        node for node in subgraph.nodes
        if subgraph.in_degree(node) >= 2
    )


def unwrap_ref_value(wrapper: RootModel | BaseModel | str) -> str | None:
    """Unwrap a ref wrapper to its string cache key, or None.

    Ref types in generated input models are RootModel[str].
    Returns the string if present, None otherwise.
    """
    ref_value = wrapper.root if isinstance(wrapper, RootModel) else wrapper
    return ref_value if isinstance(ref_value, str) else None
