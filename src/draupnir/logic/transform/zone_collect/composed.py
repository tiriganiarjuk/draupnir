"""Zone collection — conditional zone iteration and when-condition adaptation.

CC=4-8 collectors. The conditional zone is structurally different from
required/optional: each entry wraps a ref (cache key) alongside
only_when/always_when/not_when conditions that control field visibility.

adapt_when bridges the generated input model's RootModel-wrapped
ConditionalWhen to the canonical ConditionalWhen dataclass used by
conditional_build. This is necessary because datamodel-code-generator
wraps every field in RootModel, creating three layers of wrapping:
  RootModel → inner model → RootModel per field (.field, .equals, .in_)

collect_conditional produces both the properties dict (always included)
and the conditionals list (if/then/else nodes for same-section allOf).
Cross-section conditionals (dotted field paths) are filtered out by
conditional_build — they're handled at the orchestrate level via
graph traversal.
"""

from pydantic import BaseModel, RootModel

from draupnir.logic.transform.conditional_build.simple import build_conditional_entry
from draupnir.logic.transform.unwrap.simple import (
    unwrap_when_equals,
    unwrap_when_in_values,
)
from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.conditionals import ConditionalWhen
from draupnir.structure.model.schema_output import SchemaConditional


def adapt_when(when_wrapper: RootModel | None) -> ConditionalWhen | None:
    """Convert a generated ConditionalWhen RootModel to the canonical format.

    Unwraps three layers: outer RootModel → inner model → per-field RootModel.
    Determines the active predicate type:
    - equals or in_ present → value-matching condition (exists stays None)
    - neither present → existence check (exists=True)

    The canonical ConditionalWhen is consumed by conditional_build/simple.py
    which dispatches to the appropriate if/then/else builder based on
    which when-condition (only_when, always_when, not_when) is active.
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
    """Build properties and conditionals from a conditional zone dict.

    Each dict value is a RootModel wrapping a conditional entry model.
    The entry has .ref (RootModel[str] cache key) and up to one of
    .only_when/.always_when/.not_when. The property is always added to
    the schema (the field exists); the conditional controls whether
    it appears in required or is forbidden via if/then/else.

    build_conditional_entry returns None for cross-section conditionals
    (dotted field paths) — those are collected separately by the
    orchestrate layer via graph traversal.
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
