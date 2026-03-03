"""Zone collection primitives for required/optional/conditional zones.

Extracts the repeated pattern of iterating over required, optional,
and conditional zones to collect properties, required keys, and
conditional schemas. Used by all container converters across tiers.

No IO. Pure collection logic.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.functions.pure.converters.conditional import build_conditional_entry
from draupnir.structures.conditionals import ConditionalEntry
from draupnir.structures.schema_output import SchemaConditional


def collect_required_optional(
    required: dict[str, BaseModel] | None,
    optional: dict[str, BaseModel] | None,
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[str]]:
    """Build properties and required keys from required/optional zones."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    if required:
        for name, ref in required.items():
            properties[name] = build_fn(ref)
            required_keys.append(name)
    if optional:
        for name, ref in optional.items():
            properties[name] = build_fn(ref)
    return properties, required_keys


def collect_conditional(
    conditional: dict[str, ConditionalEntry] | None,
    build_fn: Callable[[BaseModel], BaseModel],
) -> tuple[dict[str, BaseModel], list[SchemaConditional]]:
    """Build properties and conditionals from a conditional zone."""
    properties: dict[str, BaseModel] = {}
    conditionals: list[SchemaConditional] = []
    if conditional:
        for name, entry in conditional.items():
            properties[name] = build_fn(entry.ref)
            cond = build_conditional_entry(
                name, entry.only_when, entry.always_when, entry.not_when,
            )
            if cond is not None:
                conditionals.append(cond)
    return properties, conditionals
