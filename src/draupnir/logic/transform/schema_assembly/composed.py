"""Schema assembly — graph-based property collection and fragment assembly.

CC=4-8. Replaces the old zone-dict-walking approach with graph edge queries.
Instead of unwrapping model.sections.required/optional zone dicts, these
functions query graph.successors() and read edge attributes for zone and
property name. This makes assembly a pure graph query — the graph is the
single source of truth for all parent-child relationships.

Fragment assembly handles two root shapes: arrays (wrapped in an "items"
property for TOML compatibility) and groups (properties inlined directly).
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
    """Iterate schema successors via graph edges to build the properties dict.

    Each edge's "name" attr becomes the property key in the output JSON Schema.
    Each edge's "zone" attr determines whether the key goes into "required".
    The built schema for each successor is looked up from context.built —
    this is either the inline schema or a SchemaRef if the node was promoted
    to $defs during per-schema compilation.
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
    """Build a standalone fragment document for TOML include files.

    Uses context.full (not .built) because the root node itself may be a
    SchemaRef in context.built if it was promoted to $defs — but the
    fragment needs the full schema as its root content.

    Arrays are wrapped in {"items": schema} because TOML root is always
    a table — bare arrays can't be represented. Groups are emitted with
    their properties directly as the fragment root.
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
