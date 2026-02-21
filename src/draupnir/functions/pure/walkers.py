"""Walk the composition tree from schema root to leaves.

Pure (with injected IO): the walker receives typed loader callables
that return validated Pydantic models. The walking logic itself is
deterministic — given the same loader responses, it always produces
the same WalkedSchema.

Walk order: schema → sections → groups/supergroups → composed → arrays.
Composed fields with type="object" become sub-groups (recursive).
Primitives are NOT loaded here — they're handled by the resolver via
name-based type adoption from a pre-loaded pool.

Uses PurePosixPath for path construction (pure, no IO).
Loaders receive PurePosixPath and handle file reading + validation.
"""

from pathlib import PurePosixPath

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawSchema,
    RawSection,
    SchemaLoaders,
    WalkedArray,
    WalkedGroup,
    WalkedSchema,
    WalkedSection,
)


# =============================================================================
# COMPOSED FIELD WALKING
# =============================================================================


def is_file_reference(value: str) -> bool:
    """Check if a field value is a file path (vs bare primitive name).

    File references contain a directory separator. Bare primitive names
    are simple identifiers like 'agent_name'.
    """
    return "/" in value


def synthesize_bare_primitive(field_name: str, type_name: str) -> RawComposed:
    """Create a synthetic RawComposed for a bare primitive field reference.

    Groups can reference primitives directly (bare name, no file path).
    The walker wraps these as thin RawComposed so the resolver can
    process them uniformly. Requirement is left None — the resolver
    inherits it from the primitive's own requirement field.
    """
    return RawComposed(name=field_name, type=type_name)


def is_structural_composed(composed: RawComposed) -> bool:
    """Check if a composed field is structural (type=object with fields)."""
    return composed.type == "object" and composed.fields is not None


def is_composed_array(composed: RawComposed) -> bool:
    """Check if a composed field is an array (type=array with items)."""
    return composed.type == "array"


def is_blocklist_composed(composed: RawComposed) -> bool:
    """Check if a composed field is a blocklist (no type, has imports)."""
    return composed.type is None and composed.imports is not None


def walk_composed_to_group(
    composed: RawComposed,
) -> WalkedGroup:
    """Walk a structural composed field as if it were a group.

    Structural composed fields (type=object with fields dict) are
    nested objects. Their fields reference primitive types by name,
    not file paths — so no file loading is needed. Each field is
    synthesized as a thin RawComposed for the resolver.
    """
    raw_group = RawGroup(
        name=composed.name,
        type="object",
        description=composed.description,
        composition=composed.composition,
        additional_properties=composed.additional_properties or False,
        fields=composed.fields or {},
    )
    thin_fields = tuple(
        synthesize_bare_primitive(name, type_name)
        for name, type_name in (composed.fields or {}).items()
    )
    return WalkedGroup(raw=raw_group, composed_fields=thin_fields)


# =============================================================================
# GROUP WALKING
# =============================================================================


def walk_group(
    raw_group: RawGroup,
    root: PurePosixPath,
    loaders: SchemaLoaders,
) -> WalkedGroup:
    """Walk a group, loading its composed fields and arrays.

    Fields dict values are file paths relative to toolcompose root.
    Each is loaded via the typed composed loader.
    Structural composed fields become sub-groups.
    """
    thin_fields: list[RawComposed] = []
    sub_groups: list[WalkedGroup] = []
    composed_arrays: list[RawComposed] = []
    for field_name, field_path in raw_group.fields.items():
        if not is_file_reference(field_path):
            thin_fields.append(synthesize_bare_primitive(field_name, field_path))
            continue
        composed = loaders.composed(root / field_path)
        if is_structural_composed(composed):
            sub_groups.append(walk_composed_to_group(composed))
        elif is_composed_array(composed):
            composed_arrays.append(composed)
        elif is_blocklist_composed(composed):
            pass  # not a property — contributes via x-not references
        else:
            thin_fields.append(composed)

    arrays = walk_group_arrays(raw_group, root, loaders)
    return WalkedGroup(
        raw=raw_group,
        composed_fields=tuple(thin_fields),
        composed_arrays=tuple(composed_arrays),
        sub_groups=tuple(sub_groups),
        arrays=tuple(arrays),
    )


def walk_group_arrays(
    raw_group: RawGroup,
    root: PurePosixPath,
    loaders: SchemaLoaders,
) -> tuple[WalkedArray, ...]:
    """Load and walk arrays referenced by a group."""
    walked: list[WalkedArray] = []
    for array_name, array_path in raw_group.arrays.items():
        raw_array = loaders.array(root / array_path)
        walked.append(walk_array(raw_array, root, loaders))
    return tuple(walked)


# =============================================================================
# ARRAY WALKING
# =============================================================================


def walk_array(
    raw_array: RawArray,
    root: PurePosixPath,
    loaders: SchemaLoaders,
) -> WalkedArray:
    """Walk an array, loading its item type group(s).

    Items can be a single $ref or a oneOf list of $refs.
    Each ref points to a group file relative to toolcompose root.
    """
    item_refs = extract_item_refs(raw_array)
    items: list[WalkedGroup] = []
    for ref_path in item_refs:
        raw_group = loaders.group(root / ref_path)
        items.append(walk_group(raw_group, root, loaders))
    return WalkedArray(raw=raw_array, items=tuple(items))


def extract_item_refs(raw_array: RawArray) -> tuple[str, ...]:
    """Extract file path references from array items.

    Handles three shapes:
    - ArrayItems with $ref (single type)
    - ArrayItems with oneOf (union)
    - tuple[RefString, ...] (reduced form)
    """
    items = raw_array.items
    if isinstance(items, tuple):
        return tuple(rs.ref for rs in items)
    if items.ref is not None:
        return (items.ref,)
    if items.one_of is not None:
        return tuple(rs.ref for rs in items.one_of)
    return ()


# =============================================================================
# SECTION WALKING
# =============================================================================


def walk_section(
    raw_section: RawSection,
    root: PurePosixPath,
    loaders: SchemaLoaders,
) -> WalkedSection:
    """Walk a section, loading its sub-component groups and arrays."""
    components: list[WalkedGroup] = []
    for comp_name, comp_path in raw_section.sub_components.items():
        raw_group = loaders.group(root / comp_path)
        components.append(walk_group(raw_group, root, loaders))
    arrays = walk_section_arrays(raw_section, root, loaders)
    return WalkedSection(
        raw=raw_section,
        components=tuple(components),
        arrays=tuple(arrays),
    )


def walk_section_arrays(
    raw_section: RawSection,
    root: PurePosixPath,
    loaders: SchemaLoaders,
) -> tuple[WalkedArray, ...]:
    """Load and walk arrays referenced by a section."""
    walked: list[WalkedArray] = []
    for array_name, array_path in raw_section.arrays.items():
        raw_array = loaders.array(root / array_path)
        walked.append(walk_array(raw_array, root, loaders))
    return tuple(walked)


# =============================================================================
# SCHEMA WALKING
# =============================================================================


def walk_schema(
    raw_schema: RawSchema,
    root: PurePosixPath,
    loaders: SchemaLoaders,
) -> WalkedSchema:
    """Walk a full schema, loading all referenced sections and groups.

    Sections dict maps JSON field names to section file paths.
    Groups dict maps JSON field names to group file paths (flat schemas).
    """
    sections: list[WalkedSection] = []
    for section_name, section_path in raw_schema.sections.items():
        raw_section = loaders.section(root / section_path)
        sections.append(walk_section(raw_section, root, loaders))
    groups: list[WalkedGroup] = []
    for group_name, group_path in raw_schema.groups.items():
        raw_group = loaders.group(root / group_path)
        groups.append(walk_group(raw_group, root, loaders))
    return WalkedSchema(
        raw=raw_schema,
        sections=tuple(sections),
        groups=tuple(groups),
        nullable_groups=raw_schema.nullable_groups,
    )
