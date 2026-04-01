"""Conditional schema building — graph-based collectors.

CC=4-8 functions. Graph-based collectors walk graph edges for
cross-section conditional schema entries. Adapts generated input
model when conditions to canonical ConditionalWhen format.

No IO. Pure model-to-model conversion.
"""

import networkx as nx
from pydantic import BaseModel, RootModel

from draupnir.logic.transform.conditional_build.simple import (
    build_root_conditional,
    resolve_cross_section_mode,
)
from draupnir.logic.transform.zone_collect.simple import (
    unwrap_when_equals,
    unwrap_when_in_values,
)
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import SchemaRootConditional


def adapt_edge_when(when_wrapper: RootModel | BaseModel | None) -> ConditionalWhen | None:
    """Convert a generated when RootModel from a graph edge to ConditionalWhen.

    Graph edges carry raw generated input model when conditions.
    Unwraps to the canonical ConditionalWhen used by conditional builders.
    """
    if when_wrapper is None:
        return None
    inner = when_wrapper.root if isinstance(when_wrapper, RootModel) else when_wrapper
    equals_val = unwrap_when_equals(inner)
    in_tuple = unwrap_when_in_values(inner)
    has_value_predicate = equals_val is not None or in_tuple is not None
    return ConditionalWhen(
        field=inner.field.root, equals=equals_val,
        in_=in_tuple, exists=None if has_value_predicate else True,
    )


def collect_section_graph_conditionals(
    section_key: str,
    section_name: str,
    graph: nx.DiGraph,
) -> list[SchemaRootConditional]:
    """Walk section → group → field edges, collect cross-section conditionals.

    For each conditional field edge, adapts the raw when conditions
    and builds a SchemaRootConditional with the path (section, group).
    """
    results: list[SchemaRootConditional] = []
    for group_key in graph.successors(section_key):
        group_name = graph[section_key][group_key]["name"]
        for field_key in graph.successors(group_key):
            field_edge = graph[group_key][field_key]
            if field_edge["zone"] != "conditional":
                continue
            adapted_only = adapt_edge_when(field_edge.get("only_when"))
            adapted_always = adapt_edge_when(field_edge.get("always_when"))
            adapted_not = adapt_edge_when(field_edge.get("not_when"))
            resolved = resolve_cross_section_mode(adapted_only, adapted_always, adapted_not)
            if resolved is not None:
                active, mode = resolved
                target_path = (section_name, group_name)
                results.append(build_root_conditional(
                    active, field_edge["name"], target_path, mode,
                ))
    return results
