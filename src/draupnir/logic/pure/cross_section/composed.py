"""Cross-section conditional collection — graph-based collectors.

CC=4-8. Walks the graph to find conditional field edges, adapts their
raw generated when-conditions to canonical ConditionalWhen format, and
builds SchemaRootConditional entries for the output schema's allOf.

The adaptation is necessary because graph edges carry when-conditions
as raw generated RootModel values (from structure/gen/input/), while the
conditional builders in simple.py expect the canonical ConditionalWhen
model (from structure/model/conditionals.py). adapt_edge_when bridges
the two representations by unwrapping RootModel layers and determining
which predicate type (equals/in_/exists) is active.
"""

import networkx as nx
from pydantic import BaseModel, RootModel

from draupnir.logic.pure.cross_section.simple import (
    build_root_conditional,
    resolve_cross_section_mode,
)
from draupnir.logic.pure.unwrap.simple import (
    unwrap_when_equals,
    unwrap_when_in_values,
)
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import SchemaRootConditional


def adapt_edge_when(when_wrapper: RootModel | BaseModel | None) -> ConditionalWhen | None:
    """Bridge between generated RootModel when-conditions and canonical ConditionalWhen.

    Generated models nest the when as RootModel[ConditionalWhen1|2|3] where
    inner fields (.field, .equals, .in_) are also RootModels. This function
    unwraps all layers and determines the predicate type: if equals or in_
    has a value, it's a value predicate; otherwise it's an existence check
    (exists=True). Returns None for absent when-conditions.
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
    """Two-level graph walk: section -> group -> field, filtering conditional edges.

    For each field edge with zone="conditional", adapts the three when-condition
    slots and passes through resolve_cross_section_mode to filter to cross-section
    only (same-section conditionals are handled at build time by transform/).
    The target_path (section_name, group_name) is built from edge "name" attrs
    to locate the field in the output schema structure.
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
