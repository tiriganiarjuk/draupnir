"""Zone collection — single-zone iteration.

CC=2-3 helpers that iterate one zone dict at a time.
Looks up pre-built schemas from the build context by cache key string.
Zone dict values are RootModel[str] wrappers — access .root for the key.
"""

from pydantic import BaseModel, RootModel

from draupnir.structure.config.build_context import BuildContext


def collect_required_optional(
    required: dict[str, RootModel] | None,
    optional: dict[str, RootModel] | None,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[str]]:
    """Build properties and required keys from required/optional zones."""
    req_props = build_zone_properties(required, context)
    opt_props = build_zone_properties(optional, context)
    properties = {**req_props, **opt_props}
    return properties, list(req_props.keys())


def build_zone_properties(
    zone: dict[str, RootModel] | None,
    context: BuildContext,
) -> dict[str, BaseModel]:
    """Build properties from a single zone dict.

    Zone dict values are RootModel[str] — .root gives the cache key.
    """
    if not zone:
        return {}
    return {name: context.built[item_ref.root] for name, item_ref in zone.items()}
