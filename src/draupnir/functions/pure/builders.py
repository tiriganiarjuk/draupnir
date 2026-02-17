"""Convert resolved models to JSON Schema output models.

Pure: takes Resolved* models, returns Schema* models.
No IO, no mutation, no untyped dicts.

The output models serialize to JSON Schema Draft 2020-12 via
model_dump(by_alias=True, exclude_none=True) at the writer boundary.
"""

from draupnir.structures import (
    ConditionalRequirement,
    ResolvedArray,
    ResolvedField,
    ResolvedGroup,
    ResolvedSchema,
    ResolvedSection,
    RequirementCondition,
    SchemaArray,
    SchemaCondition,
    SchemaConditional,
    SchemaConst,
    SchemaDocument,
    SchemaEnumConstraint,
    SchemaField,
    SchemaNotRef,
    SchemaObject,
    SchemaOneOf,
    SchemaSemanticExt,
    SemanticConstraint,
    ValidationConstraint,
)


# =============================================================================
# FIELD → SCHEMA FIELD
# =============================================================================


def build_field(field: ResolvedField) -> SchemaField:
    """Convert a ResolvedField to a SchemaField output model."""
    return SchemaField(
        type=field.json_type,
        description=field.description,
        format=field.format,
        pattern=field.pattern,
        enum=field.enum_values,
        default=field.default,
        minimum=field.minimum,
        x_validation=field.validation,
        x_not=build_not_ref(field.not_ref),
        x_semantic=build_semantic_ext(field.semantic),
    )


def build_not_ref(not_ref: str | None) -> SchemaNotRef | None:
    """Convert a not_ref string to a SchemaNotRef, or None."""
    if not_ref is None:
        return None
    return SchemaNotRef(ref=not_ref)


def build_semantic_ext(
    sc: SemanticConstraint | None,
) -> SchemaSemanticExt | None:
    """Convert a SemanticConstraint to output form, or None.

    Empty tuples become None so exclude_none=True omits them.
    """
    if sc is None:
        return None
    return SchemaSemanticExt(
        intent=sc.intent,
        severity=sc.severity,
        checks=sc.checks if sc.checks else None,
        anti_patterns=sc.anti_patterns if sc.anti_patterns else None,
    )


# =============================================================================
# REQUIREMENT → REQUIRED LIST + CONDITIONALS
# =============================================================================


def is_field_required(field: ResolvedField) -> bool:
    """Check if a field is unconditionally required."""
    req = field.requirement
    if isinstance(req, str):
        return req in ("mandatory", "required")
    return False


def classify_field_requirement(
    field: ResolvedField,
) -> tuple[str | None, SchemaConditional | None]:
    """Classify a field's requirement as required name or conditional.

    Returns (required_name, conditional):
    - If unconditionally required: (field.name, None)
    - If conditional: (None, SchemaConditional)
    - If optional/other: (None, None)
    """
    if is_field_required(field):
        return (field.name, None)
    if isinstance(field.requirement, RequirementCondition):
        cond = build_only_when_conditional(
            field.requirement.only_when, field.name,
        )
        return (None, cond)
    return (None, None)


def build_only_when_conditional(
    cond: ConditionalRequirement,
    field_name: str,
) -> SchemaConditional:
    """Build an if/then/else conditional for an only_when requirement."""
    return SchemaConditional(
        if_=build_condition_if_clause(cond),
        then_=SchemaCondition(required=(field_name,)),
        else_=SchemaCondition(properties={field_name: False}),
    )


def build_condition_if_clause(
    cond: ConditionalRequirement,
) -> SchemaCondition:
    """Build the if-clause for a conditional requirement."""
    if cond.present is not None:
        return SchemaCondition(required=(cond.field,))
    if cond.in_values is not None:
        constraint = SchemaEnumConstraint(enum=cond.in_values)
        return SchemaCondition(properties={cond.field: constraint})
    if cond.equals is not None:
        constraint = SchemaConst(const=cond.equals)
        return SchemaCondition(properties={cond.field: constraint})
    return SchemaCondition(required=(cond.field,))


# =============================================================================
# GROUP → SCHEMA OBJECT
# =============================================================================


def build_group(group: ResolvedGroup) -> SchemaObject:
    """Convert a ResolvedGroup to a SchemaObject output model."""
    properties, required, conditionals = collect_group_contents(group)
    return SchemaObject(
        description=group.description,
        properties=properties,
        required=tuple(required) if required else None,
        additional_properties=False if not group.additional_properties else None,
        all_of=tuple(conditionals) if conditionals else None,
        min_properties=1 if group.composition == "OneOf" else None,
    )


def collect_group_contents(
    group: ResolvedGroup,
) -> tuple[
    dict[str, SchemaField | SchemaObject | SchemaArray],
    list[str],
    list[SchemaConditional],
]:
    """Collect properties, required list, and conditionals from a group."""
    properties: dict[str, SchemaField | SchemaObject | SchemaArray] = {}
    required: list[str] = []
    conditionals: list[SchemaConditional] = []
    for field in group.fields:
        properties[field.name] = build_field(field)
        req_name, cond = classify_field_requirement(field)
        if req_name is not None:
            required.append(req_name)
        if cond is not None:
            conditionals.append(cond)
    for sub in group.sub_groups:
        properties[sub.name] = build_group(sub)
        if sub.name in group.required_fields:
            required.append(sub.name)
    for arr in group.arrays:
        properties[arr.name] = build_array(arr)
        if arr.name in group.required_fields:
            required.append(arr.name)
    return properties, required, conditionals


# =============================================================================
# ARRAY → SCHEMA ARRAY
# =============================================================================


def build_array(array: ResolvedArray) -> SchemaArray:
    """Convert a ResolvedArray to a SchemaArray output model."""
    return SchemaArray(
        description=array.description,
        items=build_array_items(array.items),
    )


def build_array_items(
    items: tuple[ResolvedGroup, ...],
) -> SchemaObject | SchemaOneOf:
    """Build array items: single group or oneOf wrapper."""
    if len(items) == 1:
        return build_group(items[0])
    return SchemaOneOf(one_of=tuple(build_group(g) for g in items))


# =============================================================================
# SECTION → SCHEMA OBJECT
# =============================================================================


def build_section(section: ResolvedSection) -> SchemaObject:
    """Convert a ResolvedSection to a SchemaObject output model."""
    properties: dict[str, SchemaField | SchemaObject | SchemaArray] = {}
    required: list[str] = []
    for comp in section.components:
        properties[comp.name] = build_group(comp)
        if comp.name in section.required_fields:
            required.append(comp.name)
    return SchemaObject(
        description=section.description,
        properties=properties,
        required=tuple(required) if required else None,
        additional_properties=False if not section.additional_properties else None,
        min_properties=1 if section.composition == "OneOf" else None,
    )


# =============================================================================
# SCHEMA → SCHEMA DOCUMENT
# =============================================================================


def build_schema_document(schema: ResolvedSchema) -> SchemaDocument:
    """Convert a ResolvedSchema to a SchemaDocument output model."""
    properties: dict[str, SchemaObject] = {}
    for section in schema.sections:
        properties[section.name] = build_section(section)
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"agent-{schema.name}",
        title=schema.name,
        description=schema.description,
        required=schema.required_sections if schema.required_sections else None,
        properties=properties,
        additional_properties=False if not schema.additional_properties else None,
    )
