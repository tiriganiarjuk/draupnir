"""Schema assembly — document assembly from compiled graph results.

CC=1-2 assemblers. Thin compositor that queries graph edges
and assembles a SchemaDocument from compiled results.
"""

import networkx as nx
from pydantic import BaseModel

from draupnir.logic.transform.schema_assembly.composed import collect_graph_section_properties
from draupnir.logic.transform.schema_build.simple import optional_tuple
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import SchemaDocument


def assemble_schema(
    cache_key: str,
    model: BaseModel,
    graph: nx.DiGraph,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> SchemaDocument:
    """Assemble a SchemaDocument from a compiled schema model.

    Queries graph edges from this schema node to its section successors.
    Edge attrs carry zone (required/optional) and name (property key).
    Cross-section conditionals (allOf) are applied at the orchestrate level.
    """
    properties, required_keys = collect_graph_section_properties(
        cache_key, graph, context,
    )
    schema_name = cache_key.split("/", 1)[1]
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"{schema_name}.schema.json",
        title=model.title.root,
        description=model.description.root,
        required=optional_tuple(required_keys),
        properties=properties,
        additional_properties=False,
        defs=defs or None,
    )
