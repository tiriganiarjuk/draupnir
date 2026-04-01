"""Zone collection — iterate required/optional/conditional dicts.

CC=4-8 collectors. Builds properties, required keys, and conditional
schemas from zone dicts. Conditional entries are RootModel wrappers —
unwrap .root to access the entry, then .ref.root for the cache key.
Conditional when values are adapted from generated RootModel wrappers
to the original ConditionalWhen format for downstream builders.
"""

from pydantic import BaseModel, RootModel

from draupnir.logic.transform.conditional_build.simple import build_conditional_entry
from draupnir.logic.transform.zone_collect.simple import (
    unwrap_when_equals,
    unwrap_when_in_values,
)
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import SchemaConditional


def adapt_when(when_wrapper: RootModel | None) -> ConditionalWhen | None:
    """Convert a generated ConditionalWhen RootModel to the original format.

    Generated input models wrap ConditionalWhen in RootModel, and inner
    fields (.field, .equals, .in_) are also RootModel wrappers.
    Determines active predicate: equals/in_ → value match, else → exists.
    """
    if when_wrapper is None:
        return None
    inner = when_wrapper.root
    equals_val = unwrap_when_equals(inner)
    in_tuple = unwrap_when_in_values(inner)
    has_value_predicate = equals_val is not None or in_tuple is not None
    return ConditionalWhen(
        field=inner.field.root, equals=equals_val,
        in_=in_tuple, exists=None if has_value_predicate else True,
    )


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
                name,
                adapt_when(entry.only_when),
                adapt_when(entry.always_when),
                adapt_when(entry.not_when),
            )
            if condition is not None:
                conditionals.append(condition)
    return properties, conditionals
