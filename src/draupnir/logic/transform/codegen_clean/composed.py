"""Codegen clean composed — constraint stripping state machine.

CC=4+. Imports from simple and primitive within this module.

The constraint duplication bug occurs because datamodel-code-generator copies
pattern/min_length/max_length constraints from a RootModel's root field onto
every Field that references that RootModel type. At runtime, Pydantic applies
both the RootModel's constraints (correct) and the Field's constraints
(duplicate), causing TypeError when the constraint types conflict. This
transform removes the Field-level duplicates.
"""

import re

from draupnir.logic.transform.codegen_clean.primitive import collect_rootmodel_names
from draupnir.logic.transform.codegen_clean.simple import check_rootmodel_field


def strip_redundant_constraints(content: str) -> str:
    """Remove pattern/length constraints from Fields that reference RootModels.

    datamodel-code-generator duplicates pattern and length constraints — once
    on the RootModel root field (correct) and again on every Field that uses
    that type (causes TypeError at runtime). Strip the duplicates.
    """
    rootmodel_names = collect_rootmodel_names(content)
    if not rootmodel_names:
        return content
    lines = content.split("\n")
    result: list[str] = []
    # State machine: tracks whether current line is inside an Annotated[] block
    # that references a RootModel type. Transitions:
    #   "Annotated[" on current line + next line has RootModel type -> enter state
    #   "]," on current line -> exit state
    # While in state, pattern=/min_length=/max_length= lines are stripped.
    in_rootmodel_field = False
    for line_index, line in enumerate(lines):
        stripped = line.strip()
        if "Annotated[" in stripped:
            in_rootmodel_field = check_rootmodel_field(lines, line_index, rootmodel_names)
        elif stripped == "],":
            in_rootmodel_field = False
        if in_rootmodel_field and re.match(r"\s+(pattern|min_length|max_length)=", line):
            continue
        if in_rootmodel_field:
            line = re.sub(r",?\s*(min_length|max_length)=\d+", "", line)
        result.append(line)
    return "\n".join(result)
