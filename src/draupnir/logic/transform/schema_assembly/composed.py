"""Schema assembly — graph-based property collection and fragment assembly.

CC=4-8 functions. Collects properties and required keys by querying
graph edges from schema nodes to their section successors.
Assembles fragment documents from compiled cache entries.
"""

import networkx as nx
from pydantic import BaseModel

from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import FragmentDocument


def collect_graph_section_properties(
    schema_key: str,
    graph: nx.DiGraph,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[str]]:
    """Collect properties and required keys from graph edges.

    Queries successors of a schema node. Each edge carries zone
    (required/optional/conditional) and name (property key in output).
    Required-zone edges produce required keys.
    """
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    for successor_key in graph.successors(schema_key):
        edge_data = graph[schema_key][successor_key]
        property_name = edge_data["name"]
        zone = edge_data["zone"]
        if successor_key not in context.built:
            continue
        properties[property_name] = context.built[successor_key]
        if zone == "required":
            required_keys.append(property_name)
    return properties, required_keys


def assemble_fragment(
    cache_key: str,
    output_name: str,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> FragmentDocument:
    """Assemble a FragmentDocument from a compiled cache entry.

    Uses context.full for the root (in case it's a SchemaRef in context.built).
    output_name is the fragment's enum name (e.g., 'include_success_criteria').
    """
    root_schema = context.full[cache_key]
    fragment_name = output_name.replace("_", "-")
    if hasattr(root_schema, "items"):
        properties = {"items": root_schema}
        required = ("items",)
    else:
        properties = root_schema.properties
        required = root_schema.required
    return FragmentDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"{fragment_name}.schema.json",
        title=root_schema.title or fragment_name,
        description=root_schema.description or "",
        required=required,
        properties=properties,
        additional_properties=False,
        defs=defs or None,
    )
