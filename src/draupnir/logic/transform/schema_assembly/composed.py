"""Schema assembly — zone property collection and fragment assembly.

CC=4-8 functions. Collects properties and required keys from schema
zone sets. Assembles fragment documents from compiled cache entries.
"""

from pydantic import BaseModel

from draupnir.logic.transform.schema_build.simple import unwrap_zone
from draupnir.logic.transform.zone_collect.simple import build_zone_properties
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import FragmentDocument


def collect_section_zone_properties(
    zones: BaseModel | None,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[str]]:
    """Collect properties and required keys from a schema zone set.

    Handles .required and .optional zone dicts. Each zone dict value
    is a RootModel[str] section ref — looked up from context.built.
    """
    if zones is None:
        return {}, []
    req_dict = unwrap_zone(zones.required)
    opt_dict = unwrap_zone(zones.optional)
    req_props = build_zone_properties(req_dict, context) if req_dict else {}
    opt_props = build_zone_properties(opt_dict, context) if opt_dict else {}
    return {**req_props, **opt_props}, list(req_props.keys())


def assemble_fragment(
    cache_key: str,
    context: BuildContext,
    defs: dict[str, BaseModel],
) -> FragmentDocument:
    """Assemble a FragmentDocument from a compiled cache entry.

    Uses context.full for the root (in case it's a SchemaRef in context.built).
    """
    root_schema = context.full[cache_key]
    fragment_name = cache_key.replace("/", "_")
    return FragmentDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"include_{fragment_name}",
        title=root_schema.title or fragment_name,
        description=root_schema.description or "",
        properties={"items": root_schema} if hasattr(root_schema, "items") else {},
        defs=defs or None,
    )
