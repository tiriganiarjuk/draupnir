"""Resolve type adoption chains and convert walked trees to resolved trees.

Pure: takes data structures, returns data structures. No IO.

Type adoption: composed fields reference primitive types by name.
Primitives form chains (e.g., path_exists_absolute → path_allowed_absolute
→ string). The resolver walks these chains to produce ResolvedFields with
all properties accumulated. Shallower primitives override deeper ones.
"""

from collections.abc import Sequence

from draupnir.functions.pure.stabilizers import stabilize_name
from draupnir.structures import (
    BlocklistPool,
    ComposedArrayItems,
    ForbiddenEntry,
    RawComposed,
    RawPrimitive,
    RawSchema,
    RequirementCondition,
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
    """Index primitives by name for type chain lookups.

    Detects name collisions between primitives and composed type-adopters.
    Primitives are loaded first, composed adopters appended — a collision
    means a composed file has the same name as a primitive, which is an
    error in the composition data.
    """
    pool: dict[str, RawPrimitive] = {}
    for p in primitives:
        if p.name in pool:
            raise ValueError(
                f"Type pool collision: '{p.name}' appears more than "
                f"once. Primitives and composed type-adopters must "
                f"have unique names."
            )
        pool[p.name] = p
    return pool


def build_blocklists(
    blocklist_composed: Sequence[RawComposed],
    pool: dict[str, RawPrimitive],
) -> BlocklistPool:
    """Expand blocklist composed files into ForbiddenEntry tuples.

    Each blocklist has imports referencing primitives by name.
    The primitives carry const/enum/pattern/description.
    """
    result: dict[str, tuple[ForbiddenEntry, ...]] = {}
    for composed in blocklist_composed:
        if composed.imports is None:
            continue
        entries: list[ForbiddenEntry] = []
        for ref in composed.imports:
            prim = pool.get(ref.ref)
            if prim is None:
                msg = f"Blocklist '{composed.name}' references unknown primitive '{ref.ref}'"
                raise ValueError(msg)
            entries.append(build_forbidden_entry(prim))
        result[composed.name] = tuple(entries)
    return BlocklistPool(entries=result)


def build_forbidden_entry(prim: RawPrimitive) -> ForbiddenEntry:
    """Convert a forbidden primitive to a ForbiddenEntry."""
    return ForbiddenEntry(
        name=prim.name,
        const=prim.const,
        enum=prim.enum,
        pattern=prim.pattern,
        description=prim.description,
    )


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


def expand_not_entries(
    prim: RawPrimitive,
    base: ResolvedField,
    blocklists: BlocklistPool,
) -> tuple[ForbiddenEntry, ...] | None:
    """Expand a primitive's not constraint using the blocklists dict."""
    if prim.not_constraint is not None:
        return blocklists.entries.get(prim.not_constraint.ref)
    return base.not_entries


def overlay_primitive(
    base: ResolvedField,
    prim: RawPrimitive,
    blocklists: BlocklistPool,
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
        const=prim.const if prim.const is not None else base.const,
        default=prim.default if prim.default is not None else base.default,
        minimum=prim.minimum if prim.minimum is not None else base.minimum,
        not_entries=expand_not_entries(prim, base, blocklists),
        validation=prim.validation if prim.validation is not None else base.validation,
        semantic=prim.semantic if prim.semantic is not None else base.semantic,
        items_type=prim.items.type if prim.items is not None else base.items_type,
        min_items=prim.min_items if prim.min_items is not None else base.min_items,
        max_items=prim.max_items if prim.max_items is not None else base.max_items,
        unique_items=prim.unique_items if prim.unique_items is not None else base.unique_items,
    )


def resolve_type_chain(
    type_name: str,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
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
        base = overlay_primitive(base, prim, blocklists)
    return base


# =============================================================================
# COMPOSED FIELD RESOLUTION
# =============================================================================


INVALID_REQUIREMENTS = frozenset({"optional", "mandatory_when", "prohibited_when"})


def is_selector(req: str | RequirementCondition | None) -> bool:
    """Check if a requirement value is a selector (not inherit/None)."""
    if req is None or req == "inherit":
        return False
    return True


def resolve_requirement_chain(
    composed_req: str | RequirementCondition | None,
    type_name: str,
    pool: dict[str, RawPrimitive],
    field_name: str,
) -> str | RequirementCondition:
    """Resolve requirement using one-selector-one-inherit rule.

    Walks the composed field + type chain. Exactly one level may carry
    a selector (mandatory, required, only_when). All others must be
    inherit or None. Violations fail the build.
    """
    chain = collect_type_chain(type_name, pool)
    all_reqs = [composed_req] + [p.requirement for p in chain]
    validate_requirement_values(all_reqs, field_name)
    selectors = [r for r in all_reqs if is_selector(r)]
    if len(selectors) > 1:
        raise ValueError(
            f"Field '{field_name}': multiple requirement selectors "
            f"in type chain: {selectors}. One selector, one inherit."
        )
    if len(selectors) == 1:
        return selectors[0]
    return "inherit"


def validate_requirement_values(
    reqs: Sequence[str | RequirementCondition | None],
    field_name: str,
) -> Sequence[str | RequirementCondition | None]:
    """Reject invalid requirement values. Fail fast, hard, loud.

    Returns the validated sequence unchanged for chaining.
    """
    for req in reqs:
        if isinstance(req, str) and req in INVALID_REQUIREMENTS:
            raise ValueError(
                f"Field '{field_name}': requirement '{req}' is "
                f"invalid. Valid: mandatory, required, inherit, "
                f"only_when."
            )
    return reqs


def resolve_thin_composed(
    composed: RawComposed,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedField:
    """Resolve a thin composed field (type = primitive name) to ResolvedField.

    Requirement uses one-selector-one-inherit: exactly one level in the
    chain carries the selector, all others inherit. Description from
    composed overrides the chain if set.
    """
    chain_result = resolve_type_chain(composed.type, pool, blocklists)
    requirement = resolve_requirement_chain(
        composed.requirement, composed.type, pool, composed.name,
    )
    return ResolvedField(
        name=stabilize_name(composed.name),
        json_type=chain_result.json_type,
        format=chain_result.format,
        pattern=chain_result.pattern,
        enum_values=chain_result.enum_values,
        description=composed.description if composed.description is not None else chain_result.description,
        requirement=requirement,
        const=chain_result.const,
        default=chain_result.default,
        minimum=chain_result.minimum,
        not_entries=chain_result.not_entries,
        validation=chain_result.validation,
        semantic=chain_result.semantic,
        constraint=composed.x_constraint,
        items_type=chain_result.items_type,
        min_items=chain_result.min_items,
        max_items=chain_result.max_items,
        unique_items=chain_result.unique_items,
    )


def resolve_structural_fields(
    fields: dict[str, str],
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> tuple[ResolvedField, ...]:
    """Resolve a structural composed's fields dict to ResolvedFields.

    Each value in the fields dict is a primitive type name.
    """
    resolved: list[ResolvedField] = []
    for field_name, type_name in fields.items():
        chain_result = resolve_type_chain(type_name, pool, blocklists)
        resolved.append(ResolvedField(
            name=field_name,
            json_type=chain_result.json_type,
            format=chain_result.format,
            pattern=chain_result.pattern,
            enum_values=chain_result.enum_values,
            description=chain_result.description,
            const=chain_result.const,
            default=chain_result.default,
            minimum=chain_result.minimum,
            not_entries=chain_result.not_entries,
            validation=chain_result.validation,
            semantic=chain_result.semantic,
            items_type=chain_result.items_type,
            min_items=chain_result.min_items,
            max_items=chain_result.max_items,
            unique_items=chain_result.unique_items,
        ))
    return tuple(resolved)


# =============================================================================
# COMPOSED ARRAY RESOLUTION
# =============================================================================


def resolve_composed_array_items(
    items: ComposedArrayItems,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedField:
    """Resolve composed array items to a ResolvedField.

    Items reference a primitive by name ($ref) or declare an inline
    JSON type (type). Returns a ResolvedField for the item type.
    """
    if items.ref is not None:
        return resolve_type_chain(items.ref, pool, blocklists)
    if items.type is not None:
        return ResolvedField(name="_items", json_type=items.type)
    msg = "Composed array items has neither $ref nor type"
    raise ValueError(msg)


def resolve_composed_array(
    composed: RawComposed,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedArray:
    """Resolve a composed array field to a ResolvedArray.

    The items are resolved via the primitives pool (name-based),
    not via file-based group references.
    """
    if composed.items is None:
        msg = f"Composed array {composed.name!r} has no items"
        raise ValueError(msg)
    item_field = resolve_composed_array_items(composed.items, pool, blocklists)
    return ResolvedArray(
        name=stabilize_name(composed.name),
        description=composed.description,
        items=item_field,
        requirement=composed.requirement,
        min_items=composed.min_items,
        max_items=composed.max_items,
        unique_items=composed.unique_items,
        semantic=composed.semantic,
    )


# =============================================================================
# WALKED → RESOLVED CONVERSION
# =============================================================================


def resolve_walked_group(
    group: WalkedGroup,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedGroup:
    """Convert a WalkedGroup to a ResolvedGroup.

    Resolves thin composed fields via type chain.
    Recurses into sub-groups and arrays.
    """
    fields = tuple(
        resolve_thin_composed(c, pool, blocklists)
        for c in group.composed_fields
    )
    sub_groups = tuple(
        resolve_walked_group(sg, pool, blocklists)
        for sg in group.sub_groups
    )
    file_arrays = tuple(
        resolve_walked_array(a, pool, blocklists)
        for a in group.arrays
    )
    comp_arrays = tuple(
        resolve_composed_array(c, pool, blocklists)
        for c in group.composed_arrays
    )
    return ResolvedGroup(
        name=stabilize_name(group.raw.name),
        description=group.raw.description,
        composition=group.raw.composition,
        additional_properties=group.raw.additional_properties,
        fields=fields,
        sub_groups=sub_groups,
        arrays=file_arrays + comp_arrays,
        required_fields=group.raw.required_fields,
    )


def resolve_walked_array(
    array: WalkedArray,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedArray:
    """Convert a WalkedArray to a ResolvedArray."""
    items = tuple(
        resolve_walked_group(g, pool, blocklists) for g in array.items
    )
    return ResolvedArray(
        name=stabilize_name(array.raw.name),
        description=array.raw.description,
        items=items,
    )


def resolve_walked_section(
    section: WalkedSection,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedSection:
    """Convert a WalkedSection to a ResolvedSection."""
    components = tuple(
        resolve_walked_group(g, pool, blocklists)
        for g in section.components
    )
    arrays = tuple(
        resolve_walked_array(a, pool, blocklists)
        for a in section.arrays
    )
    return ResolvedSection(
        name=stabilize_name(section.raw.name),
        description=section.raw.description,
        composition=section.raw.composition,
        additional_properties=section.raw.additional_properties,
        required_fields=section.raw.required_fields,
        components=components,
        arrays=arrays,
    )


def resolve_walked_schema(
    schema: WalkedSchema,
    pool: dict[str, RawPrimitive],
    blocklists: BlocklistPool,
) -> ResolvedSchema:
    """Convert a WalkedSchema to a ResolvedSchema."""
    sections = tuple(
        resolve_walked_section(s, pool, blocklists)
        for s in schema.sections
    )
    groups = tuple(
        resolve_walked_group(g, pool, blocklists)
        for g in schema.groups
    )
    return ResolvedSchema(
        name=schema.raw.name,
        version=schema.raw.version,
        description=schema.raw.description,
        additional_properties=schema.raw.additional_properties,
        required_sections=schema.raw.required_sections,
        optional_sections=schema.raw.optional_sections,
        sections=sections,
        groups=groups,
        required_groups=schema.raw.required_groups,
        nullable_groups=schema.nullable_groups,
    )


# =============================================================================
# SCHEMA SECTIONS BRIDGE (pre-Phase 5 compatibility)
# =============================================================================


def build_schema_sections_dict(
    schema: RawSchema,
) -> dict[str, str]:
    """Build sections dict from required + optional section names.

    Current schema YAMLs list sections by name only (no file paths).
    This bridges to the walker's format: {name: "sections/{name}.yaml"}.
    If schema.sections is already populated (post Phase 5), returns it.
    """
    if schema.sections:
        return dict(schema.sections)
    all_names = list(schema.required_sections) + list(schema.optional_sections)
    return {name: f"sections/{name}.yaml" for name in all_names}
