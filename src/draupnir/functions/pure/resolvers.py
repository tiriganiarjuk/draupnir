"""Resolve type adoption chains and convert walked trees to resolved trees.

Pure: takes data structures, returns data structures. No IO.

Type adoption: composed fields reference primitive types by name.
Primitives form chains (e.g., path_exists_absolute → path_allowed_absolute
→ string). The resolver walks these chains to produce ResolvedFields with
all properties accumulated. Shallower primitives override deeper ones.
"""

from collections.abc import Sequence

from draupnir.structures import (
    RawComposed,
    RawPrimitive,
    ResolvedArray,
    ResolvedField,
    ResolvedGroup,
    ResolvedSchema,
    ResolvedSection,
    WalkedArray,
    WalkedGroup,
    WalkedSchema,
    WalkedSection,
)

JSON_SCHEMA_TYPES = frozenset({
    "string", "integer", "boolean", "number", "array", "object",
})


# =============================================================================
# PRIMITIVES POOL
# =============================================================================


def build_primitives_pool(
    primitives: Sequence[RawPrimitive],
) -> dict[str, RawPrimitive]:
    """Index primitives by name for type chain lookups."""
    return {p.name: p for p in primitives}


# =============================================================================
# TYPE CHAIN RESOLUTION
# =============================================================================


def collect_type_chain(
    type_name: str,
    pool: dict[str, RawPrimitive],
) -> tuple[RawPrimitive, ...]:
    """Follow type references to build the full primitive chain.

    Returns primitives from shallowest to deepest.
    The deepest primitive's .type is a JSON Schema type (terminal).
    Raises ValueError on circular references or unknown types.
    """
    chain: list[RawPrimitive] = []
    current = type_name
    seen: set[str] = set()
    while current not in JSON_SCHEMA_TYPES:
        if current in seen:
            raise ValueError(f"Circular type reference: {current}")
        seen.add(current)
        if current not in pool:
            raise ValueError(f"Unknown primitive type: {current}")
        prim = pool[current]
        chain.append(prim)
        current = prim.type
    return tuple(chain)


def overlay_primitive(
    base: ResolvedField,
    prim: RawPrimitive,
) -> ResolvedField:
    """Overlay a primitive's non-None properties onto a ResolvedField.

    Returns a new ResolvedField. The primitive's properties override
    the base where set. Called shallowest-last so shallow wins.
    """
    return ResolvedField(
        name=base.name,
        json_type=base.json_type,
        format=prim.format if prim.format is not None else base.format,
        pattern=prim.pattern if prim.pattern is not None else base.pattern,
        enum_values=prim.enum if prim.enum is not None else base.enum_values,
        description=prim.description if prim.description is not None else base.description,
        requirement=base.requirement,
        default=prim.default if prim.default is not None else base.default,
        minimum=prim.minimum if prim.minimum is not None else base.minimum,
        not_ref=prim.not_constraint.ref if prim.not_constraint is not None else base.not_ref,
        validation=prim.validation if prim.validation is not None else base.validation,
        semantic=prim.semantic if prim.semantic is not None else base.semantic,
    )


def resolve_type_chain(
    type_name: str,
    pool: dict[str, RawPrimitive],
) -> ResolvedField:
    """Resolve a primitive type chain to a ResolvedField.

    Walks the chain from deepest to shallowest, each level overlaying
    its non-None properties. Returns a ResolvedField with placeholder
    name '_chain' — the caller sets the real name.
    """
    chain = collect_type_chain(type_name, pool)
    terminal_type = chain[-1].type
    base = ResolvedField(name="_chain", json_type=terminal_type)
    for prim in reversed(chain):
        base = overlay_primitive(base, prim)
    return base


# =============================================================================
# COMPOSED FIELD RESOLUTION
# =============================================================================


def resolve_thin_composed(
    composed: RawComposed,
    pool: dict[str, RawPrimitive],
) -> ResolvedField:
    """Resolve a thin composed field (type = primitive name) to ResolvedField.

    The composed field's name and requirement are authoritative.
    Description from composed overrides the chain if set.
    """
    chain_result = resolve_type_chain(composed.type, pool)
    return ResolvedField(
        name=composed.name,
        json_type=chain_result.json_type,
        format=chain_result.format,
        pattern=chain_result.pattern,
        enum_values=chain_result.enum_values,
        description=composed.description if composed.description is not None else chain_result.description,
        requirement=composed.requirement,
        default=chain_result.default,
        minimum=chain_result.minimum,
        not_ref=chain_result.not_ref,
        validation=chain_result.validation,
        semantic=chain_result.semantic,
    )


def resolve_structural_fields(
    fields: dict[str, str],
    pool: dict[str, RawPrimitive],
) -> tuple[ResolvedField, ...]:
    """Resolve a structural composed's fields dict to ResolvedFields.

    Each value in the fields dict is a primitive type name.
    """
    resolved: list[ResolvedField] = []
    for field_name, type_name in fields.items():
        chain_result = resolve_type_chain(type_name, pool)
        resolved.append(ResolvedField(
            name=field_name,
            json_type=chain_result.json_type,
            format=chain_result.format,
            pattern=chain_result.pattern,
            enum_values=chain_result.enum_values,
            description=chain_result.description,
            default=chain_result.default,
            minimum=chain_result.minimum,
            not_ref=chain_result.not_ref,
            validation=chain_result.validation,
            semantic=chain_result.semantic,
        ))
    return tuple(resolved)


# =============================================================================
# WALKED → RESOLVED CONVERSION
# =============================================================================


def resolve_walked_group(
    group: WalkedGroup,
    pool: dict[str, RawPrimitive],
) -> ResolvedGroup:
    """Convert a WalkedGroup to a ResolvedGroup.

    Resolves thin composed fields via type chain.
    Recurses into sub-groups and arrays.
    """
    fields = tuple(
        resolve_thin_composed(c, pool)
        for c in group.composed_fields
    )
    sub_groups = tuple(
        resolve_walked_group(sg, pool)
        for sg in group.sub_groups
    )
    arrays = tuple(
        resolve_walked_array(a, pool)
        for a in group.arrays
    )
    return ResolvedGroup(
        name=group.raw.name,
        description=group.raw.description,
        composition=group.raw.composition,
        additional_properties=group.raw.additional_properties,
        fields=fields,
        sub_groups=sub_groups,
        arrays=arrays,
        required_fields=group.raw.required_fields,
    )


def resolve_walked_array(
    array: WalkedArray,
    pool: dict[str, RawPrimitive],
) -> ResolvedArray:
    """Convert a WalkedArray to a ResolvedArray."""
    items = tuple(
        resolve_walked_group(g, pool) for g in array.items
    )
    return ResolvedArray(
        name=array.raw.name,
        description=array.raw.description,
        items=items,
    )


def resolve_walked_section(
    section: WalkedSection,
    pool: dict[str, RawPrimitive],
) -> ResolvedSection:
    """Convert a WalkedSection to a ResolvedSection."""
    components = tuple(
        resolve_walked_group(g, pool)
        for g in section.components
    )
    return ResolvedSection(
        name=section.raw.name,
        description=section.raw.description,
        composition=section.raw.composition,
        additional_properties=section.raw.additional_properties,
        required_fields=section.raw.required_fields,
        components=components,
    )


def resolve_walked_schema(
    schema: WalkedSchema,
    pool: dict[str, RawPrimitive],
) -> ResolvedSchema:
    """Convert a WalkedSchema to a ResolvedSchema."""
    sections = tuple(
        resolve_walked_section(s, pool)
        for s in schema.sections
    )
    return ResolvedSchema(
        name=schema.raw.name,
        version=schema.raw.version,
        description=schema.raw.description,
        additional_properties=schema.raw.additional_properties,
        required_sections=schema.raw.required_sections,
        optional_sections=schema.raw.optional_sections,
        sections=sections,
    )
