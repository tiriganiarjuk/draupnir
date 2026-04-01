"""Schema assembly — document assembly from compiled results.

CC=1-2 assemblers. Thin compositor that collects zone properties
and assembles a SchemaDocument from compiled graph results.
"""

from pydantic import BaseModel

from draupnir.logic.transform.schema_assembly.composed import collect_section_zone_properties
from draupnir.logic.transform.schema_build.simple import optional_tuple
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import SchemaDocument


def assemble_schema(
    cache_key: str,
    model: BaseModel,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> SchemaDocument:
    """Assemble a SchemaDocument from a compiled schema model.

    Collects section properties from sections + shallowsections zones,
    builds required list, attaches $defs.
    """
    sec_props, sec_req = collect_section_zone_properties(model.sections, context)
    shallow_props, shallow_req = collect_section_zone_properties(
        model.shallowsections, context,
    )
    properties = {**sec_props, **shallow_props}
    required_keys = sec_req + shallow_req
    schema_name = cache_key.split("/", 1)[1]
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=schema_name,
        title=model.title.root,
        description=model.description.root,
        required=optional_tuple(required_keys),
        properties=properties,
        additional_properties=False,
        defs=defs or None,
    )
