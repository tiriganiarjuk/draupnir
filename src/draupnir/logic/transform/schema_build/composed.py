"""Schema building — composed builders.

CC=4-8 builders. Multi-branch functions that combine context lookups
with conditional construction. Handles types where generated input
models require multiple RootModel unwraps and context.full lookups.
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
    """Convert exclude pattern refs to JSON Schema not constraint."""
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
    """Atom -> {type, pattern?, minLength?, not?, description}.

    Destructures pattern and excludes from context.full because the
    input model holds string refs, not resolved model instances.
    """
    pattern = context.full[model.pattern.root].pattern if model.pattern else None
    excludes_list = model.excludes.root if model.excludes else None
    not_constraint = build_excludes(excludes_list, context) if excludes_list else None
    min_length = model.min_length.root if model.min_length else None
    return SchemaField(
        title=model.title.root,
        type=model.type.value,
        pattern=pattern,
        min_length=min_length,
        not_=not_constraint,
        description=model.description.root,
    )
