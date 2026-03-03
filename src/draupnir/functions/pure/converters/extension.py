"""Field extension converters for semantic and constraint annotations.

Converts Verdandi SemanticBlock and ConstraintRule models into their
JSON Schema extension equivalents (x-semantic, x-constraint). Also
handles min_length resolution and description concatenation.

No IO. Pure model-to-model conversion.
"""

from pydantic import BaseModel

from draupnir.structures.field import ConstraintRule, SemanticBlock
from draupnir.structures.fields import Atom, Element
from draupnir.structures.schema_output import (
    SchemaConstraintBlock,
    SchemaConstraintEntry,
    SchemaSemanticExt,
)
from draupnir.structures.simple_containers import VerdandiField


def convert_semantic(block: SemanticBlock) -> SchemaSemanticExt:
    """SemanticBlock -> SchemaSemanticExt for JSON Schema output."""
    return SchemaSemanticExt(
        intent=block.intent or "",
        severity=block.severity or "warning",
        checks=block.checks,
        anti_patterns=block.anti_patterns,
    )


def convert_constraint_rule(rule: ConstraintRule) -> SchemaConstraintEntry:
    """ConstraintRule -> SchemaConstraintEntry for JSON Schema output."""
    fields = {
        "rule": rule.rule,
        "severity": rule.severity,
        "reason": rule.reason,
        "field": rule.field,
    }
    if rule.order is not None:
        fields["order"] = rule.order
    if rule.values is not None:
        fields["in"] = rule.values
    return SchemaConstraintEntry.model_validate(fields)


def convert_constraints(
    rules: tuple[ConstraintRule, ...],
) -> SchemaConstraintBlock:
    """Tuple of ConstraintRules -> SchemaConstraintBlock."""
    entries = tuple(convert_constraint_rule(cr) for cr in rules)
    return SchemaConstraintBlock(constraints=entries)


def extract_type_min_length(field_type: BaseModel) -> int | None:
    """Extract min_length from a Verdandi type model (Atom or Element->Atom)."""
    if isinstance(field_type, Atom):
        return field_type.min_length
    if isinstance(field_type, Element) and isinstance(field_type.inherits, Atom):
        return field_type.inherits.min_length
    return None


def resolve_field_min_length(field: VerdandiField, type_min: int | None) -> int | None:
    """Return field override only when it raises above the type default."""
    if field.min_length is None:
        return None
    atom_min = type_min or 0
    if field.min_length > atom_min:
        return field.min_length
    return None


def concat_field_description(field: VerdandiField) -> str:
    """Build concatenated description from field + type descriptions."""
    field_desc = field.description.strip()
    type_desc = field.type.description
    if type_desc and type_desc.strip() != field_desc:
        return f"{field_desc}\n{type_desc.strip()}"
    return field_desc
