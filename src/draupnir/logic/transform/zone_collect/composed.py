"""Zone collection — iterate required/optional/conditional dicts.

CC=4-8 collectors. Builds properties, required keys, and conditional
schemas from zone dicts. Conditional entries are RootModel wrappers —
unwrap .root to access the entry, then .ref.root for the cache key.
"""

from pydantic import BaseModel, RootModel

from draupnir.logic.transform.conditional_build.simple import build_conditional_entry
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import SchemaConditional


def collect_conditional(
    conditional: dict[str, RootModel] | None,
    context: BuildContext,
) -> tuple[dict[str, BaseModel], list[SchemaConditional]]:
    """Build properties and conditionals from a conditional zone.

    Each dict value is a RootModel wrapping a conditional entry with
    .ref (RootModel[str] cache key), .only_when, .always_when, .not_when.
    """
    properties: dict[str, BaseModel] = {}
    conditionals: list[SchemaConditional] = []
    if conditional:
        for name, entry_wrapper in conditional.items():
            entry = entry_wrapper.root
            properties[name] = context.built[entry.ref.root]
            condition = build_conditional_entry(
                name, entry.only_when, entry.always_when, entry.not_when,
            )
            if condition is not None:
                conditionals.append(condition)
    return properties, conditionals
