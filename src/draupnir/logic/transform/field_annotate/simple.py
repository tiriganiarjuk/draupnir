"""Field annotation — branching converters.

CC=1-3 converters for field metadata. Transform structure models
to schema output models with a small number of branches.

Functions that need the inner type's properties (description, min_length)
receive the built inner schema directly, not the raw input model ref.
Includes RootModel unwrapping helpers for generated input model fields.
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


def optional_tuple_from(items: list[str] | None) -> tuple[str, ...] | None:
    """Convert a list to tuple, or None if empty/absent."""
    return tuple(items) if items else None


def conditional_entries(
    *pairs: tuple[str, str | int | None],
) -> dict[str, str | int]:
    """Build dict from (field_name, field_value) pairs, excluding None values."""
    return {field_name: field_value for field_name, field_value in pairs if field_value is not None}


def min_length_default(type_min: int | None) -> int:
    """Return type min_length or 0 if unset."""
    return type_min if type_min is not None else 0


def resolve_field_min_length(field_min: int | None, type_min: int | None) -> int | None:
    """Return field override only when it raises above the type default."""
    if field_min is None:
        return None
    atom_min = min_length_default(type_min)
    if field_min > atom_min:
        return field_min
    return None


def concat_field_description(field_description: str, type_description: str | None) -> str:
    """Build concatenated description from field + type descriptions."""
    field_desc = field_description.strip()
    if type_description and type_description.strip() != field_desc:
        return f"{field_desc}\n{type_description.strip()}"
    return field_desc


def extract_type_min_length(inner_schema: BaseModel) -> int | None:
    """Extract min_length from a built inner schema.

    Only SchemaField has min_length. SchemaOneOfField, SchemaArray, etc.
    do not — returns None for those.
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
    """SemanticBlock -> SchemaSemanticExt for JSON Schema output."""
    return SchemaSemanticExt(
        intent=unwrap_or_default(block.intent, ""),
        severity=unwrap_or_default(block.severity, "warning"),
        checks=optional_tuple_from(unwrap_list_or_none(block.checks)),
        anti_patterns=optional_tuple_from(unwrap_list_or_none(block.anti_patterns)),
    )


def convert_constraint_rule(rule: BaseModel) -> SchemaConstraintEntry:
    """ConstraintRule -> SchemaConstraintEntry for JSON Schema output."""
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
    """Convert constraint RootModel wrapper to tuple of entries."""
    rules_list = constraint_wrapper.root
    if not rules_list:
        return ()
    return tuple(convert_constraint_rule(rule) for rule in rules_list)
