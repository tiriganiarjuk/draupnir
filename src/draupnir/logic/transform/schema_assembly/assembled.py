"""Schema assembly — SchemaDocument construction from compiled graph results.

CC=1-2. Thin compositor that delegates property collection to composed.py
(graph edge queries) and packages the result into a SchemaDocument with
metadata from the input model (title, description).

Cross-section conditionals (allOf) are NOT wired here — they're applied
at the orchestrate level via model_copy because computing them requires
graph traversal across the pure/cross_section zone boundary.
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
    """Wire graph-based property collection into a SchemaDocument.

    The schema_id includes ".schema.json" suffix for compatibility with
    the established output format. Title and description are accessed
    via .root because the input model wraps them in RootModel[str].
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
