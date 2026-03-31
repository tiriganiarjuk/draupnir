"""Zone collection — single-zone iteration.

CC=2-3 helpers that iterate one zone dict at a time.
"""

from collections.abc import Callable

from pydantic import BaseModel


def collect_required_optional(
    required: dict[str, BaseModel] | None,
    optional: dict[str, BaseModel] | None,
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[str]]:
    """Build properties and required keys from required/optional zones."""
    req_props = build_zone_properties(required, build_fn)
    opt_props = build_zone_properties(optional, build_fn)
    properties = {**req_props, **opt_props}
    return properties, list(req_props.keys())


def build_zone_properties(
    zone: dict[str, BaseModel] | None,
    build_fn: Callable[[BaseModel], BaseModel],
) -> dict[str, BaseModel]:
    """Build properties from a single zone dict."""
    if not zone:
        return {}
    return {name: build_fn(model) for name, model in zone.items()}
