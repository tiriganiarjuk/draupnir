"""Graph build composed — ref extraction and graph construction.

CC=4-8. Stack-based model walker that extracts cache ref strings from
generated input models, and graph builder that creates a NetworkX DiGraph.

Generated input models wrap values in RootModel classes:
  - Ref types: RootModel[str] where .root is a cache key string
  - Zone dicts: RootModel[dict[str, RefType] | None]
  - Lists: RootModel[list[RefType] | None]
The walker unwraps these via .root and inspects the underlying values.
"""

import networkx as nx
from pydantic import BaseModel, RootModel

from draupnir.logic.transform.graph_build.simple import base_model_children, is_cache_ref


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


def build_graph(cache: dict[str, BaseModel]) -> nx.DiGraph:
    """Build a dependency graph from a populated cache.

    Each cache entry becomes a node with the model as an attribute.
    Each string ref found in the model becomes a directed edge from
    the parent (referencing model) to the child (referenced model).
    """
    graph = nx.DiGraph()
    for cache_key, model in cache.items():
        level_name = cache_key.split("/", 1)[0]
        graph.add_node(cache_key, model=model, level=level_name)
    for cache_key, model in cache.items():
        for ref_target in extract_refs(model):
            if ref_target in cache:
                graph.add_edge(cache_key, ref_target)
    return graph
