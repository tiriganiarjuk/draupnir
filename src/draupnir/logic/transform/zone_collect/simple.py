"""Zone collection — single-zone iteration.

CC=2-3 helpers that iterate one zone dict at a time. Zone dicts come
from generated input models where each value is a RootModel[str]
wrapping a cache key string. The cache key resolves to a pre-built
schema node in BuildContext.built.
"""

from pydantic import BaseModel, RootModel

from draupnir.structure.config.build_context import BuildContext


def collect_required_optional(
    required: dict[str, RootModel] | None,
    optional: dict[str, RootModel] | None,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[str]]:
    """Build properties dict and required keys list from required/optional zones.

    Required zone entries go into both properties and the required list.
    Optional zone entries go into properties only. Both zones are merged
    into a single properties dict — JSON Schema does not distinguish them
    structurally except via the required array.
    """
    req_props = build_zone_properties(required, context)
    opt_props = build_zone_properties(optional, context)
    properties = {**req_props, **opt_props}
    return properties, list(req_props.keys())


def build_zone_properties(
    zone: dict[str, RootModel] | None,
    context: BuildContext,
) -> dict[str, BaseModel]:
    """Build properties from a single zone dict.

    Zone dict values are RootModel[str] wrappers. Access .root to get
    the cache key string, then look up the built schema from context.
    Returns empty dict for None zones (zone not present on the model).
    """
    if not zone:
        return {}
    return {name: context.built[item_ref.root] for name, item_ref in zone.items()}
