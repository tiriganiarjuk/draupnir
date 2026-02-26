"""Complex container and top-level builders.

Converts Group, Array, Superarray, Section, Shallowsection into JSON
Schema output models. Handles $defs: shared models get a $defs entry
and subsequent references become $ref pointers.

No IO. Pure model-to-model conversion with $defs tracking.
"""

from pydantic import BaseModel

from draupnir.functions.pure.build_fields import (
    build_conditional_entry,
    build_field,
    build_verdandi_field,
)
from draupnir.structures.complex_containers import (
    Array,
    ArrayOneOf,
    Group,
    Superarray,
    SuperarrayOneOf,
)
from draupnir.structures.fields import Union_
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaConditional,
    SchemaObject,
    SchemaOneOf,
    SchemaOneOfField,
    SchemaRef,
    SchemaTupleArray,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    Tuple_,
    VerdandiField,
)
from draupnir.structures.top_level import (
    Section,
    Shallowsection,
)


def defs_key(cache_key: str) -> str:
    """Convert cache key to $defs key: 'simplegroup/foo' -> 'simplegroup__foo'."""
    return cache_key.replace("/", "__")


def build_or_ref(
    model: BaseModel,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> BaseModel:
    """Build schema for a model, or return $ref if shared."""
    cache_key = reverse.get(id(model))
    if cache_key and cache_key in shared:
        def_name = defs_key(cache_key)
        if def_name not in defs:
            defs[def_name] = build_model(model, reverse, shared, defs)
        return SchemaRef(ref=f"#/$defs/{def_name}")
    return build_model(model, reverse, shared, defs)


def build_simplegroup_refs(
    simplegroup: Simplegroup,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaObject:
    """Simplegroup -> {type: object} with $defs-aware field building."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    for zone, is_required in ((simplegroup.required, True), (simplegroup.optional, False)):
        if zone:
            for name, ref in zone.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)
                if is_required:
                    required_keys.append(name)
    conditionals: list[SchemaConditional] = []
    if simplegroup.conditional:
        for name, entry in simplegroup.conditional.items():
            properties[name] = build_or_ref(entry.ref, reverse, shared, defs)
            conditionals.append(
                build_conditional_entry(name, entry.only_when, entry.always_when, entry.not_when),
            )
    return SchemaObject(
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=simplegroup.description,
    )


def build_tuple_refs(
    tuple_model: Tuple_,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaTupleArray:
    """Tuple -> {prefixItems, items: false} with $defs-aware item building."""
    prefix = tuple(build_or_ref(item, reverse, shared, defs) for item in tuple_model.items)
    return SchemaTupleArray(
        prefix_items=prefix,
        description=tuple_model.description,
        min_items=len(prefix),
        max_items=len(prefix),
    )


def build_simplearray_refs(
    simplearray: Simplearray,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaArray:
    """Simplearray -> {type: array, items} with $defs-aware item building."""
    return SchemaArray(
        items=build_or_ref(simplearray.items, reverse, shared, defs),
        description=simplearray.description,
    )


def build_union_refs(
    union_model: Union_,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaOneOfField:
    """Union -> {oneOf: [member schemas or $refs]}."""
    members = tuple(
        build_or_ref(member, reverse, shared, defs)
        for member in union_model.union
    )
    return SchemaOneOfField(one_of=members, description=union_model.description)


def build_model(
    model: BaseModel,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> BaseModel:
    """Dispatch any Verdandi model to its builder."""
    if isinstance(model, Simplegroup):
        return build_simplegroup_refs(model, reverse, shared, defs)
    if isinstance(model, Tuple_):
        return build_tuple_refs(model, reverse, shared, defs)
    if isinstance(model, Simplearray):
        return build_simplearray_refs(model, reverse, shared, defs)
    if isinstance(model, Union_):
        return build_union_refs(model, reverse, shared, defs)
    if isinstance(model, Group):
        return build_group(model, reverse, shared, defs)
    if isinstance(model, Array):
        return build_array(model, reverse, shared, defs)
    if isinstance(model, Superarray):
        return build_superarray(model, reverse, shared, defs)
    if isinstance(model, Section):
        return build_section(model, reverse, shared, defs)
    if isinstance(model, Shallowsection):
        return build_shallowsection(model, reverse, shared, defs)
    if isinstance(model, VerdandiField):
        return build_verdandi_field(model)
    return build_field(model)


def build_array(
    array: Array,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaArray:
    """Array -> {type: array, items: object_or_oneOf}."""
    if isinstance(array.items, ArrayOneOf):
        item_schemas = tuple(
            build_or_ref(member, reverse, shared, defs) for member in array.items.one_of
        )
        items = SchemaOneOf(one_of=item_schemas)
    else:
        items = build_or_ref(array.items, reverse, shared, defs)
    return SchemaArray(items=items, description=array.description)


def build_superarray(
    superarray: Superarray,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaArray:
    """Superarray -> {type: array, items: object_or_oneOf}."""
    if isinstance(superarray.items, SuperarrayOneOf):
        item_schemas = tuple(
            build_or_ref(member, reverse, shared, defs)
            for member in superarray.items.one_of
        )
        items = SchemaOneOf(one_of=item_schemas)
    else:
        items = build_or_ref(superarray.items, reverse, shared, defs)
    return SchemaArray(items=items, description=superarray.description)


def build_group_properties(
    group: Group,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> tuple[dict[str, BaseModel], list[str], list[SchemaConditional]]:
    """Extract properties, required keys, and conditionals from a group."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    conditionals: list[SchemaConditional] = []

    if group.fields:
        if group.fields.required:
            for name, ref in group.fields.required.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)
                required_keys.append(name)
        if group.fields.optional:
            for name, ref in group.fields.optional.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)
        if group.fields.conditional:
            for name, entry in group.fields.conditional.items():
                properties[name] = build_or_ref(entry.ref, reverse, shared, defs)
                conditionals.append(
                    build_conditional_entry(name, entry.only_when, entry.always_when, entry.not_when),
                )

    if group.containers:
        if group.containers.required:
            for name, ref in group.containers.required.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)
                required_keys.append(name)
        if group.containers.optional:
            for name, ref in group.containers.optional.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)
        if group.containers.conditional:
            for name, entry in group.containers.conditional.items():
                properties[name] = build_or_ref(entry.ref, reverse, shared, defs)
                conditionals.append(
                    build_conditional_entry(name, entry.only_when, entry.always_when, entry.not_when),
                )

    return properties, required_keys, conditionals


def build_group(
    group: Group,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaObject:
    """Group -> {type: object, properties, required, allOf?}."""
    properties, required_keys, conditionals = build_group_properties(
        group, reverse, shared, defs,
    )
    return SchemaObject(
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=group.description,
    )


def build_section(
    section: Section,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaObject:
    """Section -> {type: object, properties (components)}."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    for name, component in section.components.items():
        properties[name] = build_or_ref(component, reverse, shared, defs)
        required_keys.append(name)
    return SchemaObject(
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        description=section.description,
    )


def build_shallowsection(
    shallowsection: Shallowsection,
    reverse: dict[int, str],
    shared: frozenset[str],
    defs: dict[str, BaseModel],
) -> SchemaObject:
    """Shallowsection -> {type: object, fields + containers}."""
    properties: dict[str, BaseModel] = {}
    required_keys: list[str] = []
    conditionals: list[SchemaConditional] = []

    if shallowsection.required:
        for name, ref in shallowsection.required.items():
            properties[name] = build_or_ref(ref, reverse, shared, defs)
            required_keys.append(name)
    if shallowsection.optional:
        for name, ref in shallowsection.optional.items():
            properties[name] = build_or_ref(ref, reverse, shared, defs)

    if shallowsection.conditional:
        for name, entry in shallowsection.conditional.items():
            properties[name] = build_or_ref(entry.ref, reverse, shared, defs)
            conditionals.append(
                build_conditional_entry(name, entry.only_when, entry.always_when, entry.not_when),
            )

    if shallowsection.containers:
        if shallowsection.containers.required:
            for name, ref in shallowsection.containers.required.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)
                required_keys.append(name)
        if shallowsection.containers.optional:
            for name, ref in shallowsection.containers.optional.items():
                properties[name] = build_or_ref(ref, reverse, shared, defs)

    return SchemaObject(
        properties=properties,
        required=tuple(required_keys) if required_keys else None,
        additional_properties=False,
        all_of=tuple(conditionals) if conditionals else None,
        description=shallowsection.description,
    )
