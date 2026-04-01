"""Graph build simple — ref identification, model inspection, subgraph analysis.

CC=1-3. Ref identification checks whether a string is a cache key
(level/name format with a known Level prefix). Model inspection detects
zone set models by field name presence. Subgraph analysis computes
per-schema $defs candidates via induced subgraph in-degree.

RootModel unwrapping has moved to pure/unwrap/simple.py.
"""

import networkx as nx
from pydantic import BaseModel

from draupnir.logic.pure.graph_build.primitive import is_known_level, ref_prefix
from draupnir.structure.config.edge_ref import EdgeRef


def is_cache_ref(value: str) -> bool:
    """Compose prefix extraction + level check to identify cache ref strings.

    Must contain a slash (level/name format) AND the prefix must be a
    known Level member. This filters out plain strings that happen to
    contain slashes (e.g., file paths in descriptions).
    """
    return "/" in value and is_known_level(ref_prefix(value))


def base_model_children(model: BaseModel) -> list[BaseModel | str]:
    """Iterate model fields via Pydantic's __iter__ and keep traversable children.

    Filters to BaseModel (nested models to recurse into) and str (potential
    cache ref strings to check). Skips None fields and non-model scalars.
    """
    return [value for _name, value in model if isinstance(value, (BaseModel, str))]


def has_zone_fields(model: BaseModel) -> bool:
    """Detect zone set models by checking for required + optional field names.

    Zone sets (GroupFields, SchemaSections, SectionContainers, etc.) always
    have required/optional/conditional fields. Checking for the first two
    is sufficient — no non-zone model uses both field names.
    """
    field_names = {name for name, _ in model}
    return "required" in field_names and "optional" in field_names


def edge_ref_to_attrs(edge_ref: EdgeRef) -> dict[str, str | BaseModel]:
    """Flatten an EdgeRef into a kwargs dict for nx.DiGraph.add_edge.

    NetworkX stores edge attributes as key-value pairs. The when-condition
    fields are only included when present to avoid polluting non-conditional
    edges with None values that would need filtering downstream.
    """
    attrs: dict[str, str | BaseModel] = {"zone": edge_ref.zone, "name": edge_ref.name}
    for when_field in ("only_when", "always_when", "not_when"):
        when_value = getattr(edge_ref, when_field)
        if when_value is not None:
            attrs[when_field] = when_value
    return attrs


def schema_shared_keys(schema_key: str, graph: nx.DiGraph) -> frozenset[str]:
    """Compute per-schema $defs candidates via induced subgraph in-degree.

    Extracts descendants, builds the induced subgraph, then finds nodes
    with in-degree >= 2 within that subgraph. These are referenced by
    2+ parents in this schema's tree — they should be extracted to $defs
    and replaced with $ref to avoid duplication in the output JSON.

    Per-schema rather than global because the same node may be shared
    in one schema's tree but unique in another's.
    """
    descendants = nx.descendants(graph, schema_key)
    subgraph = graph.subgraph(descendants)
    return frozenset(
        node for node in subgraph.nodes
        if subgraph.in_degree(node) >= 2
    )
