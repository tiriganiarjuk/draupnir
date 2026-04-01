"""Field annotation — branching converters.

CC=1-3 converters for field metadata. These bridge the gap between
Verdandi's two-level type system (type definitions + field instances)
and JSON Schema's flat property model where all metadata lives on the
property itself.

Key design decisions:
- Description concatenation: field description + type description are
  joined with newline, unless they're identical (avoid duplication).
- min_length override: field min_length only applies when it raises above
  the type's default — never lowers it (the type's constraint is the floor).
- Semantic/constraint extensions: Verdandi-specific x-semantic and
  x-constraint blocks are converted to JSON Schema extension keywords.

RootModel unwrapping helpers handle the generated input model's wrapper
layers. conditional_entries builds dicts that exclude None values so
Pydantic's exclude_none serialization produces clean JSON Schema output.
"""

from pydantic import BaseModel, RootModel

from draupnir.structure.model.schema_output import (
    FieldMeta,
    SchemaConstraintBlock,
    SchemaConstraintEntry,
    SchemaField,
    SchemaSemanticExt,
)


def unwrap_or_default(wrapper: RootModel | None, default: str) -> str:
    """Unwrap a RootModel[str | None] or return default if absent."""
    return wrapper.root if wrapper else default


def unwrap_string_or_none(wrapper: RootModel | None) -> str | None:
    """Unwrap a RootModel[str | None] or return None if absent."""
    return wrapper.root if wrapper else None


def unwrap_list_or_none(wrapper: RootModel | None) -> list[str] | None:
    """Unwrap a RootModel[list[str] | None] or return None if absent."""
    return wrapper.root if wrapper else None


def optional_tuple(items: list[str] | None) -> tuple[str, ...] | None:
    """Convert a list to tuple, or None if empty/absent.

    Parallel to the generic version in schema_build/simple.py — kept local
    because same-level cross-module imports are banned.
    """
    return tuple(items) if items else None


def conditional_entries(
    *pairs: tuple[str, str | int | None],
) -> dict[str, str | int]:
    """Build dict from (field_name, field_value) pairs, excluding None values.

    Used by default_override, field_overrides, extension_overrides to produce
    sparse update dicts that only contain fields with actual values. These
    dicts are passed to model_copy(update=...) to selectively annotate schemas.
    """
    return {field_name: field_value for field_name, field_value in pairs if field_value is not None}


def min_length_default(type_min: int | None) -> int:
    """Return type min_length or 0 if unset."""
    return type_min if type_min is not None else 0


def resolve_field_min_length(field_min: int | None, type_min: int | None) -> int | None:
    """Return field override only when it raises above the type's min_length.

    The type's min_length is the floor constraint. A field can tighten it
    (raise the minimum) but not loosen it. Returns None when the field's
    value doesn't exceed the type default, which means the type constraint
    is sufficient and no field-level override is needed.
    """
    if field_min is None:
        return None
    atom_min = min_length_default(type_min)
    if field_min > atom_min:
        return field_min
    return None


def concat_field_description(field_description: str, type_description: str | None) -> str:
    """Build concatenated description from field + type descriptions.

    Joins field description (always present) with type description on a
    newline, unless they're identical (avoids "X\nX" in output). The field
    description takes priority as the first line since it's more specific.
    """
    field_desc = field_description.strip()
    if type_description and type_description.strip() != field_desc:
        return f"{field_desc}\n{type_description.strip()}"
    return field_desc


def extract_type_min_length(inner_schema: BaseModel) -> int | None:
    """Extract min_length from a built inner schema, or None if not applicable.

    Only SchemaField carries min_length (it maps to atom/element types).
    SchemaOneOfField, SchemaArray, and other composite types don't have
    string-level constraints — returns None so the field override logic
    in resolve_field_min_length treats the type floor as 0.
    """
    if isinstance(inner_schema, SchemaField):
        return inner_schema.min_length
    return None


def default_override(
    default_value: str | int | bool | list[str] | None,
) -> dict[str, str | int | bool | list[str]]:
    """Return default update if field has a default value."""
    return conditional_entries(("default", default_value))


def field_overrides(
    field_min: int | None,
    field_const: str | None,
    meta: FieldMeta,
) -> dict[str, str | int]:
    """Return SchemaField-specific overrides (min_length, const)."""
    return conditional_entries(("min_length", meta.min_length), ("const", field_const))


def extension_overrides(
    meta: FieldMeta,
) -> dict[str, SchemaSemanticExt | SchemaConstraintBlock]:
    """Return extension overrides (semantic, constraint)."""
    return conditional_entries(("x_semantic", meta.semantic), ("x_constraint", meta.constraint))


def convert_semantic(block: BaseModel) -> SchemaSemanticExt:
    """SemanticBlock -> SchemaSemanticExt for JSON Schema x-semantic extension.

    Verdandi semantic blocks carry validation intent (what the value means),
    severity, allowed checks, and anti-patterns. These become x-semantic
    in the output schema for downstream tooling to interpret.
    """
    return SchemaSemanticExt(
        intent=unwrap_or_default(block.intent, ""),
        severity=unwrap_or_default(block.severity, "warning"),
        checks=optional_tuple(unwrap_list_or_none(block.checks)),
        anti_patterns=optional_tuple(unwrap_list_or_none(block.anti_patterns)),
    )


def convert_constraint_rule(rule: BaseModel) -> SchemaConstraintEntry:
    """ConstraintRule -> SchemaConstraintEntry for JSON Schema x-constraint.

    Uses model_validate rather than direct construction because the field
    set is dynamic — "order" and "in" are only included when present.
    The "in_" Python field maps to "in" in the JSON Schema output (alias).
    """
    fields: dict[str, str | int | list[str] | None] = {
        "rule": rule.rule.root,
        "severity": rule.severity.root,
        "reason": rule.reason.root,
        "field": unwrap_string_or_none(rule.field),
    }
    order = unwrap_string_or_none(rule.order)
    if order:
        fields["order"] = order
    in_values = unwrap_list_or_none(rule.in_)
    if in_values:
        fields["in"] = in_values
    return SchemaConstraintEntry.model_validate(fields)


def convert_constraints(
    constraint_wrapper: RootModel,
) -> tuple[SchemaConstraintEntry, ...]:
    """Convert constraint RootModel wrapper to tuple of SchemaConstraintEntry.

    The constraint wrapper's .root is a list of constraint rule models.
    Returns empty tuple for empty lists (preserves the constraint block
    structure but signals "no rules" to downstream).
    """
    rules_list = constraint_wrapper.root
    if not rules_list:
        return ()
    return tuple(convert_constraint_rule(rule) for rule in rules_list)
