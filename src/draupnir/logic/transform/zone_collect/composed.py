"""Zone collection — iterate required/optional/conditional dicts.

CC=4-8 collectors. Builds properties, required keys, and conditional
schemas from zone dicts.
"""

from collections.abc import Callable

from pydantic import BaseModel

from draupnir.logic.transform.conditional_build.simple import build_conditional_entry
from draupnir.structure.model.schema_output import SchemaConditional


def collect_conditional(
    conditional: dict[str, BaseModel] | None,
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
