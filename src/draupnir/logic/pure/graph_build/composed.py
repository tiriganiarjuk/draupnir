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

from draupnir.logic.pure.graph_build.simple import (
    base_model_children,
    edge_ref_to_attrs,
    has_zone_fields,
    is_cache_ref,
    sibling_entry_names,
)
from draupnir.logic.pure.unwrap.simple import (
    unwrap_ref_value,
    unwrap_when_field,
    unwrap_zone_dict,
)
from draupnir.structure.config.edge_ref import EdgeRef


def root_model_children(model: RootModel) -> list[BaseModel | str]:
    """Branch on the three shapes RootModel.root can take in generated models.

    Dict: zone dicts map field names to ref wrappers — yield all values.
    List/tuple: ordered collections (items, members) — yield all elements.
    Single value: a direct ref string or nested model — yield as one-item list.

    Type-checks each value before yielding because dicts/lists may also
    contain None entries from optional fields.
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
    """Walk the model tree iteratively via an explicit stack to find all cache ref strings.

    Uses a stack rather than recursion because the model tree depth is
    unbounded (RootModel nesting can be arbitrary). Each node is either
    a RootModel (unwrap via root_model_children) or a BaseModel (iterate
    via base_model_children). Children that are strings get tested as
    cache refs; children that are models get pushed for further traversal.
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
    """Locate zone sets at both the model level and within its fields.

    A group model IS a zone set (it has required/optional/conditional).
    A section model CONTAINS a zone set (its .containers field is one).
    Both patterns need to be found so extract_model_refs can walk
    every zone dict for ref extraction with proper zone annotation.
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
    """Unwrap a required or optional zone dict and produce an EdgeRef per entry.

    Two layers of unwrapping: the zone itself is RootModel[dict | None],
    and each dict value is RootModel[str] wrapping a cache key. Both
    layers are handled by the simple-level unwrap helpers. Entries whose
    cache key doesn't exist in the cache are silently skipped (defensive
    against partial loads).
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
    """Unwrap a conditional zone dict and produce EdgeRefs with when-conditions.

    Three layers of unwrapping: the zone is RootModel[dict | None], each
    dict value is RootModel[ConditionalEntry], and the entry's .ref is
    RootModel[str]. The when-condition fields (only_when/always_when/not_when)
    are preserved as raw RootModel values on the EdgeRef — they're adapted
    to canonical ConditionalWhen later by pure/cross_section at collection time.
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
    """Combine zone-aware extraction with fallback flat extraction.

    First pass: find all zone sets and extract refs with zone annotations
    (required/optional/conditional). Second pass: run extract_refs for a
    flat walk — any ref NOT already found via zones gets zone="direct".

    This two-pass approach ensures fields outside zone sets (e.g.,
    atom.pattern, field.type) still get edges, while zone-managed refs
    carry their zone metadata for assembly and conditional collection.
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


def node_predicate_violations(graph: nx.DiGraph, node: str) -> list[str]:
    """Report predicate targets on one container that name no sibling."""
    names = sibling_entry_names(graph, node)
    violations: list[str] = []
    for _, _, data in graph.out_edges(node, data=True):
        for mode in ("only_when", "always_when", "not_when"):
            target = unwrap_when_field(data.get(mode))
            if target is None or target.startswith(".") or target in names:
                continue
            violations.append(
                f"{node}: {data['name']}.{mode} targets '{target}', "
                f"which is not a field of this container",
            )
    return violations


def subtree_build_order(root_key: str, graph: nx.DiGraph) -> list[str]:
    """Filter the global topological sort to just this root's subtree.

    Uses nx.descendants to find the reachable subgraph, then intersects
    with the reversed topological sort to get leaf-first build order.
    Includes root_key itself (needed for fragment compilation where the
    root is the built node). Excludes schema-level nodes because schemas
    are assembled separately after all their children are built.
    """
    descendants = nx.descendants(graph, root_key) | {root_key}
    return [
        node for node in reversed(list(nx.topological_sort(graph)))
        if node in descendants and graph.nodes[node]["level"] != "schema"
    ]


def build_graph(cache: dict[str, BaseModel]) -> nx.DiGraph:
    """Two-pass construction: first add all nodes, then extract edges.

    Pass 1: each cache entry becomes a node with its model and level
    stored as node attributes (level is derived from the cache key prefix).
    Pass 2: extract_model_refs walks each model's zone sets and direct
    fields to produce EdgeRefs, which are flattened to edge attributes.

    The resulting DiGraph is the single source of truth for all parent-child
    relationships, zone annotations, and when-conditions. Schema assembly,
    $defs detection, and cross-section conditional collection all query
    this graph rather than re-walking the input models.
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
