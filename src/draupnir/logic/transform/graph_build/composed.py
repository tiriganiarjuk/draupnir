"""Graph build composed — ref extraction, zone-aware edge data.

CC=4-8. Stack-based model walker that extracts cache ref strings from
generated input models. Zone-aware extractors that produce EdgeRef lists
with zone metadata (required/optional/conditional + when conditions).

Generated input models wrap values in RootModel classes:
  - Ref types: RootModel[str] where .root is a cache key string
  - Zone dicts: RootModel[dict[str, RefType] | None]
  - Conditional entries: RootModel[union] with .ref + .only_when/.always_when/.not_when
"""

import networkx as nx
from pydantic import BaseModel, RootModel

from draupnir.logic.transform.graph_build.simple import (
    base_model_children,
    edge_ref_to_attrs,
    has_zone_fields,
    is_cache_ref,
    unwrap_ref_value,
    unwrap_zone_dict,
)
from draupnir.structure.config.edge_ref import EdgeRef


def root_model_children(model: RootModel) -> list[BaseModel | str]:
    """Unwrap a RootModel and return inspectable children.

    Handles the three root shapes: dict (zone dicts), list/tuple
    (items, members), or single value (ref string, nested model).
    """
    root = model.root
    if isinstance(root, dict):
        return [value for value in root.values() if isinstance(value, (BaseModel, str))]
    if isinstance(root, (list, tuple)):
        return [item for item in root if isinstance(item, (BaseModel, str))]
    if isinstance(root, (str, BaseModel)):
        return [root]
    return []


def extract_refs(model: BaseModel) -> list[str]:
    """Extract all cache ref strings from a generated input model.

    Stack-based walk: for each model, get children (unwrapping RootModel
    or iterating BaseModel fields), then classify each child as string
    ref (collect) or nested model (push to stack).
    """
    refs: list[str] = []
    stack: list[BaseModel] = [model]
    while stack:
        current = stack.pop()
        if isinstance(current, RootModel):
            children = root_model_children(current)
        else:
            children = base_model_children(current)
        for child in children:
            if isinstance(child, str):
                if is_cache_ref(child):
                    refs.append(child)
            else:
                stack.append(child)
    return refs


def find_zone_sets(model: BaseModel) -> list[BaseModel]:
    """Find all zone sets in a model (the model itself + zone-having fields).

    Zone sets have required/optional/conditional structure. A model may
    itself be a zone set, and may also contain zone set fields (e.g.,
    a schema model with a sections zone set as a field value).
    """
    sets: list[BaseModel] = []
    if has_zone_fields(model):
        sets.append(model)
    for _field_name, field_value in model:
        if isinstance(field_value, BaseModel) and has_zone_fields(field_value):
            sets.append(field_value)
    return sets


def extract_zone_dict_refs(
    zone_wrapper: RootModel | None,
    zone_name: str,
    cache_keys: set[str],
) -> list[EdgeRef]:
    """Extract EdgeRefs from a required or optional zone dict.

    Unwraps the zone RootModel to its dict, then unwraps each entry
    to its cache key string. Returns an EdgeRef per valid ref.
    """
    zone_dict = unwrap_zone_dict(zone_wrapper)
    if zone_dict is None:
        return []
    refs: list[EdgeRef] = []
    for entry_name, ref_wrapper in zone_dict.items():
        ref_target = unwrap_ref_value(ref_wrapper)
        if ref_target is not None and ref_target in cache_keys:
            refs.append(EdgeRef(target=ref_target, zone=zone_name, name=entry_name))
    return refs


def extract_conditional_refs(
    cond_wrapper: RootModel | None,
    cache_keys: set[str],
) -> list[EdgeRef]:
    """Extract EdgeRefs from a conditional zone dict.

    Conditional entries have a .ref field plus when-condition fields
    (only_when, always_when, not_when). Returns an EdgeRef per valid
    conditional ref, carrying the raw when-condition values.
    """
    cond_dict = unwrap_zone_dict(cond_wrapper)
    if cond_dict is None:
        return []
    refs: list[EdgeRef] = []
    for entry_name, entry_wrapper in cond_dict.items():
        entry = entry_wrapper.root if isinstance(entry_wrapper, RootModel) else entry_wrapper
        if not hasattr(entry, "ref"):
            continue
        ref_target = unwrap_ref_value(entry.ref)
        if ref_target is None or ref_target not in cache_keys:
            continue
        refs.append(EdgeRef(
            target=ref_target, zone="conditional", name=entry_name,
            only_when=getattr(entry, "only_when", None),
            always_when=getattr(entry, "always_when", None),
            not_when=getattr(entry, "not_when", None),
        ))
    return refs


def extract_model_refs(
    model: BaseModel,
    cache_keys: set[str],
) -> list[EdgeRef]:
    """Extract all EdgeRefs from a model, zone-aware where applicable.

    For models with zone sets: extracts refs from required/optional/conditional
    zones with metadata. For remaining refs (direct fields like atom.pattern):
    adds with zone="direct". Zone refs take precedence — a ref found via zone
    extraction is not duplicated as a direct ref.
    """
    refs: list[EdgeRef] = []
    zone_targets: set[str] = set()
    for zone_set in find_zone_sets(model):
        for zone_name in ("required", "optional"):
            zone_refs = extract_zone_dict_refs(
                getattr(zone_set, zone_name, None), zone_name, cache_keys,
            )
            refs.extend(zone_refs)
            zone_targets.update(edge_ref.target for edge_ref in zone_refs)
        cond_refs = extract_conditional_refs(
            getattr(zone_set, "conditional", None), cache_keys,
        )
        refs.extend(cond_refs)
        zone_targets.update(edge_ref.target for edge_ref in cond_refs)
    for ref_target in extract_refs(model):
        if ref_target in cache_keys and ref_target not in zone_targets:
            refs.append(EdgeRef(target=ref_target, zone="direct", name=""))
    return refs


def subtree_build_order(root_key: str, graph: nx.DiGraph) -> list[str]:
    """Return non-schema descendants of root_key in reverse topological order.

    Includes root_key itself if it's not a schema node. Used to determine
    the build order for per-schema and per-fragment compilation.
    """
    descendants = nx.descendants(graph, root_key) | {root_key}
    return [
        node for node in reversed(list(nx.topological_sort(graph)))
        if node in descendants and graph.nodes[node]["level"] != "schema"
    ]


def build_graph(cache: dict[str, BaseModel]) -> nx.DiGraph:
    """Build a dependency graph from a populated cache.

    Each cache entry becomes a node with the model as an attribute.
    Edges carry zone metadata: zone (required/optional/conditional/direct),
    name (field name in parent dict), and for conditionals: when conditions.
    """
    graph = nx.DiGraph()
    cache_keys = set(cache.keys())
    for cache_key, model in cache.items():
        level_name = cache_key.split("/", 1)[0]
        graph.add_node(cache_key, model=model, level=level_name)
    for cache_key, model in cache.items():
        for edge_ref in extract_model_refs(model, cache_keys):
            graph.add_edge(cache_key, edge_ref.target, **edge_ref_to_attrs(edge_ref))
    return graph
