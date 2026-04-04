"""Schema building — composed builders.

CC=4-8 builders. Handle types where the generated input model requires
multiple RootModel unwrap layers combined with context lookups.

build_atom is the most complex primitive type: it resolves pattern from
a separate pattern model (via context.full ref lookup), optionally builds
an excludes constraint (NOT clause with one or more patterns), and extracts
min_length — all from separately wrapped RootModel fields.

build_excludes converts pattern refs into JSON Schema "not" constraints.
A single exclude becomes not:{pattern:...}; multiple become
not:{anyOf:[{pattern:...}, ...]}.
"""

from pydantic import BaseModel, RootModel

from draupnir.structure.config.build_context import BuildContext
from draupnir.structure.model.schema_output import (
    SchemaAnyOfConstraint,
    SchemaField,
    SchemaPatternConstraint,
)



def build_excludes(
    exclude_refs: list[RootModel],
    context: BuildContext,
) -> SchemaPatternConstraint | SchemaAnyOfConstraint:
    """Convert exclude pattern refs to JSON Schema "not" constraint.

    Each ref points to a pattern model in context.full whose .pattern
    field holds the regex string. Single pattern → SchemaPatternConstraint
    (renders as not:{pattern:...}). Multiple → SchemaAnyOfConstraint
    wrapping each pattern (renders as not:{anyOf:[{pattern:...}, ...]}).
    """
    patterns = [context.full[pattern_ref.root].pattern for pattern_ref in exclude_refs]
    if len(patterns) == 1:
        return SchemaPatternConstraint(pattern=patterns[0])
    return SchemaAnyOfConstraint(
        any_of=tuple(
            SchemaPatternConstraint(pattern=pattern_string)
            for pattern_string in patterns
        ),
    )


def build_atom(model: BaseModel, context: BuildContext) -> SchemaField:
    """Atom -> SchemaField with optional pattern, minLength, and not constraint.

    Atoms are the leaf value types in Verdandi (string, integer, boolean,
    number). The pattern and excludes fields are string refs to separate
    pattern-level models — resolved via context.full to get the actual
    regex strings. This indirection exists because patterns are shared
    across atoms and may appear in $defs.
    """
    pattern = context.full[model.pattern.root].pattern if model.pattern else None
    excludes_list = model.excludes.root if model.excludes else None
    not_constraint = build_excludes(excludes_list, context) if excludes_list else None
    min_length = model.min_length.root if model.min_length else None
    max_length = model.max_length.root if model.max_length else None
    return SchemaField(
        title=model.title.root,
        type=model.type.value,
        pattern=pattern,
        min_length=min_length,
        max_length=max_length,
        not_=not_constraint,
        description=model.description.root,
    )


def resolve_array_constraints(
    model: BaseModel,
) -> dict[str, int | bool | None]:
    """Extract optional array constraints from a generated input model.

    Returns kwargs suitable for SchemaArray construction. Defaults
    min_items to 1 (Verdandi arrays are non-empty) when unspecified.
    Works with Simplearray, Array, and Superarray input models — all
    carry the same optional min_items/max_items/unique_items fields.
    """
    return {
        "min_items": model.min_items.root if model.min_items else 1,
        "max_items": model.max_items.root if model.max_items else None,
        "unique_items": model.unique_items.root if model.unique_items else None,
    }


