"""Convert resolved models to JSON Schema output models.

Pure: takes Resolved* models, returns Schema* models.
No IO, no mutation, no untyped dicts.

The output models serialize to JSON Schema Draft 2020-12 via
model_dump(by_alias=True, exclude_none=True) at the writer boundary.
"""

from draupnir.structures import (
    ConditionalRequirement,
    ConstraintEntry,
    ForbiddenEntry,
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
    SchemaConstraintBlock,
    SchemaConstraintEntry,
    SchemaDocument,
    SchemaEnumConstraint,
    SchemaField,
    SchemaForbiddenEntry,
    SchemaNestedPath,
    SchemaNotBlock,
    SchemaNullType,
    SchemaNullableObject,
    SchemaObject,
    SchemaOneOf,
    SchemaRootConditional,
    SchemaSemanticExt,
    SemanticConstraint,
    ValidationConstraint,
)


# =============================================================================
# FIELD → SCHEMA FIELD
# =============================================================================


def build_field(
    field: ResolvedField,
) -> SchemaField | SchemaArray:
    """Convert a ResolvedField to a SchemaField or SchemaArray.

    Array-type primitives (json_type="array" with items_type) produce
    a SchemaArray. All other fields produce a SchemaField.
    """
    if field.json_type == "array" and field.items_type is not None:
        return build_field_array(field)
    return SchemaField(
        type=field.json_type,
        description=field.description,
        const=field.const,
        format=field.format,
        pattern=field.pattern,
        enum=field.enum_values,
        default=field.default,
        minimum=field.minimum,
        x_validation=field.validation,
        x_not=build_not_block(field.not_entries),
        x_semantic=build_semantic_ext(field.semantic),
        x_constraint=build_constraint_block(field.constraint),
    )


def build_field_array(field: ResolvedField) -> SchemaArray:
    """Convert an array-type ResolvedField to a SchemaArray."""
    return SchemaArray(
        description=field.description,
        items=SchemaField(type=field.items_type),
        min_items=field.min_items,
        max_items=field.max_items,
        unique_items=field.unique_items,
        x_semantic=build_semantic_ext(field.semantic),
    )


def build_not_block(
    entries: tuple[ForbiddenEntry, ...] | None,
) -> SchemaNotBlock | None:
    """Convert expanded forbidden entries to a SchemaNotBlock."""
    if entries is None:
        return None
    return SchemaNotBlock(
        forbidden=tuple(
            SchemaForbiddenEntry(
                name=e.name,
                const=e.const,
                enum=e.enum,
                pattern=e.pattern,
                description=e.description,
            )
            for e in entries
        ),
    )


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


def build_constraint_block(
    entries: tuple[ConstraintEntry, ...] | None,
) -> SchemaConstraintBlock | None:
    """Convert ConstraintEntry tuple to a SchemaConstraintBlock."""
    if entries is None:
        return None
    return SchemaConstraintBlock(
        constraints=tuple(
            SchemaConstraintEntry(
                rule=e.rule,
                field=e.field,
                severity=e.severity,
                reason=e.reason,
            )
            for e in entries
        ),
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


def is_cross_group_conditional(cond: ConditionalRequirement) -> bool:
    """Check if a conditional references a field in another group.

    Cross-group conditionals use dot-path field references like
    'task.return.return_mode'. These cannot be emitted as local
    conditionals — they must be deferred to the schema root.
    """
    return "." in cond.field


def classify_field_requirement(
    field: ResolvedField,
) -> tuple[str | None, SchemaConditional | None]:
    """Classify a field's requirement as required name or conditional.

    Returns (required_name, conditional):
    - If unconditionally required: (field.name, None)
    - If conditional (local): (None, SchemaConditional)
    - If conditional (cross-group): (None, None) — deferred
    - If optional/other: (None, None)
    """
    if is_field_required(field):
        return (field.name, None)
    if isinstance(field.requirement, RequirementCondition):
        if is_cross_group_conditional(field.requirement.only_when):
            return (None, None)  # deferred to schema root (Phase 4)
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


def classify_array_requirement(
    arr: ResolvedArray,
    required_fields: tuple[str, ...],
) -> tuple[str | None, SchemaConditional | None]:
    """Classify an array's requirement as required name or conditional.

    Two sources of requiredness:
    - File-ref arrays: name appears in parent group's required_fields
    - Composed arrays: carry their own .requirement field
    """
    if arr.name in required_fields:
        return (arr.name, None)
    if arr.requirement is None:
        return (None, None)
    if isinstance(arr.requirement, str):
        if arr.requirement in ("mandatory", "required"):
            return (arr.name, None)
        return (None, None)
    if isinstance(arr.requirement, RequirementCondition):
        cond = build_only_when_conditional(
            arr.requirement.only_when, arr.name,
        )
        return (None, cond)
    return (None, None)


# =============================================================================
# GROUP → SCHEMA OBJECT
# =============================================================================


def build_group(group: ResolvedGroup) -> SchemaObject:
    """Convert a ResolvedGroup to a SchemaObject output model."""
    properties, required, conditionals = collect_group_contents(group)
    if group.composition == "AllOf" and not required:
        required = list(properties.keys())
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
        req_name, cond = classify_array_requirement(arr, group.required_fields)
        if req_name is not None:
            required.append(req_name)
        if cond is not None:
            conditionals.append(cond)
    return properties, required, conditionals


# =============================================================================
# ARRAY → SCHEMA ARRAY
# =============================================================================


def build_array(array: ResolvedArray) -> SchemaArray:
    """Convert a ResolvedArray to a SchemaArray output model."""
    return SchemaArray(
        description=array.description,
        items=build_array_items(array.items),
        min_items=array.min_items,
        max_items=array.max_items,
        unique_items=array.unique_items,
        x_semantic=build_semantic_ext(array.semantic),
    )


def build_array_items(
    items: tuple[ResolvedGroup, ...] | ResolvedField,
) -> SchemaObject | SchemaOneOf | SchemaField:
    """Build array items: field, single group, or oneOf wrapper."""
    if isinstance(items, ResolvedField):
        return build_field(items)
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
    for arr in section.arrays:
        properties[arr.name] = build_array(arr)
        if arr.name in section.required_fields:
            required.append(arr.name)
    if section.composition == "AllOf" and not required:
        required = list(properties.keys())
    return SchemaObject(
        description=section.description,
        properties=properties,
        required=tuple(required) if required else None,
        additional_properties=False if not section.additional_properties else None,
        min_properties=1 if section.composition == "OneOf" else None,
    )


# =============================================================================
# CROSS-SECTION CONDITIONALS (deferred to schema root)
# =============================================================================


def collect_deferred_conditionals(
    schema: ResolvedSchema,
) -> tuple[SchemaRootConditional, ...]:
    """Find cross-group conditionals and build root-level allOf.

    Scans both section-nested groups and root-level groups.
    """
    result: list[SchemaRootConditional] = []
    for section in schema.sections:
        for group in section.components:
            result.extend(
                scan_group_for_deferred(
                    group, (section.name, group.name),
                ),
            )
    for group in schema.groups:
        result.extend(
            scan_group_for_deferred(group, (group.name,)),
        )
    return tuple(result)


def scan_group_for_deferred(
    group: ResolvedGroup,
    path: tuple[str, ...],
) -> list[SchemaRootConditional]:
    """Scan a group tree for cross-section conditionals."""
    result: list[SchemaRootConditional] = []
    for field in group.fields:
        if not isinstance(field.requirement, RequirementCondition):
            continue
        if not is_cross_group_conditional(field.requirement.only_when):
            continue
        result.append(build_root_conditional(
            field.requirement.only_when, field.name, path,
        ))
    for sub in group.sub_groups:
        result.extend(
            scan_group_for_deferred(sub, path + (sub.name,)),
        )
    return result


def build_root_conditional(
    cond: ConditionalRequirement,
    field_name: str,
    field_path: tuple[str, ...],
) -> SchemaRootConditional:
    """Build a root-level if/then/else for a cross-section conditional."""
    return SchemaRootConditional(
        if_=build_root_if_clause(cond),
        then_=build_nested_required(field_path, field_name),
        else_=build_nested_forbidden(field_path, field_name),
    )


def build_root_if_clause(
    cond: ConditionalRequirement,
) -> SchemaNestedPath:
    """Build the nested if-clause for a cross-section conditional."""
    segments = tuple(cond.field.split("."))
    if cond.in_values is not None:
        leaf = SchemaEnumConstraint(enum=cond.in_values)
        return build_nested_property(segments, leaf)
    if cond.equals is not None:
        leaf = SchemaConst(const=cond.equals)
        return build_nested_property(segments, leaf)
    return build_nested_required(segments[:-1], segments[-1])


def build_nested_property(
    segments: tuple[str, ...],
    leaf: SchemaEnumConstraint | SchemaConst,
) -> SchemaNestedPath:
    """Wrap segments as nested properties with a constraint leaf."""
    if len(segments) == 1:
        return SchemaNestedPath(properties={segments[0]: leaf})
    return SchemaNestedPath(properties={
        segments[0]: build_nested_property(segments[1:], leaf),
    })


def build_nested_required(
    segments: tuple[str, ...],
    field_name: str,
) -> SchemaNestedPath:
    """Wrap segments as nested properties ending with required."""
    if len(segments) == 0:
        return SchemaNestedPath(required=(field_name,))
    return SchemaNestedPath(properties={
        segments[0]: build_nested_required(segments[1:], field_name),
    })


def build_nested_forbidden(
    segments: tuple[str, ...],
    field_name: str,
) -> SchemaNestedPath:
    """Wrap segments as nested properties ending with {field: false}."""
    if len(segments) == 0:
        return SchemaNestedPath(properties={field_name: False})
    return SchemaNestedPath(properties={
        segments[0]: build_nested_forbidden(segments[1:], field_name),
    })


# =============================================================================
# SCHEMA → SCHEMA DOCUMENT
# =============================================================================


def build_schema_document(schema: ResolvedSchema) -> SchemaDocument:
    """Convert a ResolvedSchema to a SchemaDocument output model."""
    properties: dict[str, SchemaObject | SchemaNullableObject] = {}
    for section in schema.sections:
        properties[section.name] = build_section(section)
    for group in schema.groups:
        built = build_group(group)
        if group.name in schema.nullable_groups:
            properties[group.name] = wrap_nullable(built)
        else:
            properties[group.name] = built
    required = build_required_list(schema)
    deferred = collect_deferred_conditionals(schema)
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id=f"{schema.name}-schema-v{schema.version}",
        title=schema.name,
        description=schema.description,
        required=required if required else None,
        properties=properties,
        additional_properties=False if not schema.additional_properties else None,
        all_of=deferred if deferred else None,
    )


def wrap_nullable(obj: SchemaObject) -> SchemaNullableObject:
    """Wrap a SchemaObject as nullable: oneOf [object, null]."""
    return SchemaNullableObject(
        one_of=(obj, SchemaNullType()),
        description=obj.description,
    )


def build_required_list(
    schema: ResolvedSchema,
) -> tuple[str, ...]:
    """Merge required sections and required groups into one list."""
    required = list(schema.required_sections) + list(schema.required_groups)
    return tuple(required)
