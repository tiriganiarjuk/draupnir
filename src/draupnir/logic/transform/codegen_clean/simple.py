"""Codegen clean simple — RootModel field classifier.

CC=1-3. No cross-module imports.

Predicate for identifying Annotated fields that reference RootModel types.
This is the gate that the composed-level state machine uses to decide
whether to strip constraints from a given Field block. The look-ahead
approach (check next line after 'Annotated[') works because
datamodel-code-generator always puts the type on the line following
the Annotated opening bracket.
"""


def check_rootmodel_field(lines: list[str], index: int, rootmodel_names: set[str]) -> bool:
    """Check if the Annotated field at this line references a RootModel type.

    Looks ahead one line from the Annotated[ opening to extract type tokens
    (split on |). If any of those type names are in the RootModel set, this
    field's constraints are duplicates of the RootModel's own constraints
    and must be removed by the composed-level state machine.
    """
    next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
    type_tokens = {token.strip() for token in next_line.rstrip(",").split("|")}
    return bool(type_tokens & rootmodel_names)
