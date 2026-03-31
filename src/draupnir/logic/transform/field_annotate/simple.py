"""Field annotation — branching converters.

CC=2-3 converters for field metadata. Transform structure models
to schema output models with a small number of branches.
"""

from pydantic import BaseModel

from draupnir.structure.model.field import ConstraintRule, SemanticBlock
from draupnir.structure.model.fields import Atom, Element
from draupnir.structure.model.schema_output import (
    FieldMeta,
    SchemaArray,
    SchemaConstraintBlock,
    SchemaConstraintEntry,
    SchemaField,
    SchemaOneOfField,
    SchemaSemanticExt,
)
from draupnir.structure.model.simple_containers import VerdandiField


def conditional_entries(
    *pairs: tuple[str, str | int | None],
) -> dict[str, str | int]:
    """Build dict from (field_name, field_value) pairs, excluding None values."""
    return {field_name: field_value for field_name, field_value in pairs if field_value is not None}


def min_length_default(type_min: int | None) -> int:
    """Return type min_length or 0 if unset."""
    return type_min if type_min is not None else 0


def resolve_field_min_length(field: VerdandiField, type_min: int | None) -> int | None:
    """Return field override only when it raises above the type default."""
    if field.min_length is None:
        return None
    atom_min = min_length_default(type_min)
    if field.min_length > atom_min:
        return field.min_length
    return None


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
        **conditional_entries(("order", rule.order), ("in", rule.values)),
    }
    return SchemaConstraintEntry.model_validate(fields)


def convert_constraints(
    rules: tuple[ConstraintRule, ...],
) -> SchemaConstraintBlock:
    """Tuple of ConstraintRules -> SchemaConstraintBlock."""
    entries = tuple(convert_constraint_rule(rule) for rule in rules)
    return SchemaConstraintBlock(constraints=entries)


def concat_field_description(field: VerdandiField) -> str:
    """Build concatenated description from field + type descriptions."""
    field_desc = field.description.strip()
    type_desc = field.type.description
    if type_desc and type_desc.strip() != field_desc:
        return f"{field_desc}\n{type_desc.strip()}"
    return field_desc


def is_element_with_atom(field_type: BaseModel) -> bool:
    """Check if field_type is an Element that inherits from Atom."""
    return isinstance(field_type, Element) and isinstance(field_type.inherits, Atom)


def extract_type_min_length(field_type: BaseModel) -> int | None:
    """Extract min_length from a Verdandi type model (Atom or Element->Atom)."""
    if isinstance(field_type, Atom):
        return field_type.min_length
    if is_element_with_atom(field_type):
        return field_type.inherits.min_length
    return None


def default_override(
    field: VerdandiField,
) -> dict[str, str]:
    """Return default update if field has a default value."""
    return conditional_entries(("default", field.default))


def field_overrides(
    field: VerdandiField,
    meta: FieldMeta,
) -> dict[str, str | int]:
    """Return SchemaField-specific overrides (min_length, const)."""
    return conditional_entries(("min_length", meta.min_length), ("const", field.const))


def extension_overrides(
    meta: FieldMeta,
) -> dict[str, SchemaSemanticExt | SchemaConstraintBlock]:
    """Return extension overrides (semantic, constraint)."""
    return conditional_entries(("x_semantic", meta.semantic), ("x_constraint", meta.constraint))


def compute_field_metadata(field: VerdandiField) -> FieldMeta:
    """Compute description, min_length override, semantic, and constraint."""
    combined = concat_field_description(field)
    semantic = convert_semantic(field.semantic) if field.semantic else None
    constraint = convert_constraints(field.constraint) if field.constraint else None
    type_min = extract_type_min_length(field.type)
    override = resolve_field_min_length(field, type_min)
    return FieldMeta(
        description=combined, min_length=override,
        semantic=semantic, constraint=constraint,
    )
