"""Frozen Pydantic models for the Draupnir schema generator.

All models are frozen (immutable) and contain NO methods.
All logic lives in standalone functions in other modules.

YAML shape matching: Raw models mirror the YAML structure exactly so that
Model.model_validate(yaml_dict) works directly. Pydantic aliases handle
YAML keys that aren't valid Python identifiers (e.g., $ref, not).
"""

from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


# =============================================================================
# SUB-STRUCTURE MODELS (nested within higher-level YAML)
# =============================================================================


class ValidationConstraint(BaseModel):
    """Filesystem existence check attached to a primitive.

    YAML shape: {instruction: str, severity: str}
    """

    model_config = ConfigDict(frozen=True)

    instruction: str
    severity: str


class SemanticConstraint(BaseModel):
    """Quality/semantic check attached to a primitive.

    YAML shape: {intent: str, checks: [str], anti_patterns: [str], severity: str}
    """

    model_config = ConfigDict(frozen=True)

    intent: str
    checks: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()
    severity: str


class ConstraintEntry(BaseModel):
    """Resolver constraint attached to a composed field.

    YAML shape: {rule: str, field?: str, severity: str, reason: str, ...}
    Emitted as x-constraint in generated schema. Enforced by resolver.

    Inter-field constraints (not_equal, not_subpath_of, required_when) use
    ``field`` to name the target. Intra-field constraints (tuple_ordered)
    omit ``field`` and may carry rule-specific keys (e.g., ``order``).
    Extra keys are preserved and passed through to the schema.
    """

    model_config = ConfigDict(frozen=True, extra="allow")

    rule: str  # e.g., "not_equal", "not_subpath_of", "tuple_ordered"
    field: str | None = None  # target field; None for intra-field rules
    severity: str
    reason: str


class ConditionalRequirement(BaseModel):
    """Conditional requirement — field required only when another field matches.

    YAML shape: {only_when: {field: str, equals?: str|bool, in?: [str], present?: bool}}
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    field: str
    equals: str | bool | None = None
    present: bool | None = None
    in_values: tuple[str, ...] | None = Field(default=None, alias="in")


class RequirementCondition(BaseModel):
    """Wrapper for the only_when conditional requirement.

    YAML shape: {only_when: ConditionalRequirement}
    """

    model_config = ConfigDict(frozen=True)

    only_when: ConditionalRequirement


class NotConstraint(BaseModel):
    """JSON Schema 'not' constraint referencing a blocklist.

    YAML shape: {$ref: PATH_BLOCKLIST}
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    ref: str = Field(alias="$ref")  # e.g., "PATH_BLOCKLIST"


class PrimitiveArrayItems(BaseModel):
    """Items type for array-type primitives.

    YAML shape: {type: string}
    Only used by primitives with type=array (e.g., role_expertise).
    """

    model_config = ConfigDict(frozen=True)

    type: str


class RefString(BaseModel):
    """A single $ref reference.

    YAML shape: {$ref: some_name}
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    ref: str = Field(alias="$ref")


class ArrayItems(BaseModel):
    """Items definition for an array.

    YAML shape 1 (single ref): {$ref: context_item}
    YAML shape 2 (explicit union): {oneOf: [{$ref: entry}, {$ref: include}]}
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    ref: str | None = Field(default=None, alias="$ref")
    one_of: tuple[RefString, ...] | None = Field(default=None, alias="oneOf")


class ComposedArrayItems(BaseModel):
    """Items for a composed array field.

    Two shapes:
    - $ref to primitive name: {$ref: guardrails_constraint}
    - Inline JSON type: {type: integer}

    Distinct from ArrayItems which references groups by file path.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    ref: str | None = Field(default=None, alias="$ref")
    type: str | None = None


# =============================================================================
# RAW TYPES (from YAML loading — Phase 2 validators produce these)
# =============================================================================


class RawPrimitive(BaseModel):
    """Primitive field type as loaded from YAML.

    Primitives are the type system — no variants, no collisions.
    Referenced by name from composed fields (type adoption).

    Requirement can be a string ("mandatory", "required", "optional",
    "inherit") or a conditional dict ({only_when: ...}).
    Some primitives use const instead of description.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str
    type: str  # parent primitive name or json type ("string", "integer", "boolean")
    requirement: str | RequirementCondition
    description: str | None = None
    const: str | None = None  # fixed value (e.g., return_metrics)
    format: str | None = None
    pattern: str | None = None
    enum: tuple[str, ...] | None = None
    default: str | bool | int | None = None
    minimum: int | None = None
    not_constraint: NotConstraint | None = Field(default=None, alias="not")
    validation: ValidationConstraint | None = None
    semantic: SemanticConstraint | None = None
    # Array-type primitives only (type == "array"):
    items: PrimitiveArrayItems | None = None
    min_items: int | None = Field(default=None, alias="minItems")
    max_items: int | None = Field(default=None, alias="maxItems")
    unique_items: bool | None = Field(default=None, alias="uniqueItems")


class RawComposed(BaseModel):
    """Composed field as loaded from YAML.

    Four shapes:
    - Thin: adopts a primitive type (type = primitive name).
    - Structural: an object with its own fields (type = "object").
    - Array: array with primitive items (type = "array").
    - Blocklist: pattern composition (imports list of $refs, no type field).

    Requirement can be string or conditional dict.
    The name field is the STABLE JSON field name — never changes per stage.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str
    type: str | None = None  # primitive name, "object", "array", or absent
    requirement: str | RequirementCondition | None = None
    description: str | None = None
    # Structural composed only (type == "object"):
    composition: str | None = None  # "AllOf", "OneOf"
    additional_properties: bool | None = None
    fields: dict[str, str] | None = None  # field_name → primitive type name
    # Blocklist pattern (no type field):
    imports: tuple[RefString, ...] | None = None
    # Composed array (type == "array"):
    items: ComposedArrayItems | None = None
    min_items: int | None = Field(default=None, alias="minItems")
    max_items: int | None = Field(default=None, alias="maxItems")
    unique_items: bool | None = Field(default=None, alias="uniqueItems")
    semantic: SemanticConstraint | None = None
    x_constraint: tuple[ConstraintEntry, ...] | None = Field(
        default=None, alias="x-constraint",
    )


class RawGroup(BaseModel):
    """Group of composed fields. Also covers supergroups.

    Groups reference composed fields by file path.
    Supergroups additionally reference arrays by file path.
    Both have the same structure — supergroups just use the arrays dict.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: str  # "object"
    description: str | None = None
    composition: str | None = None  # "AllOf", "OneOf", "Mixed"
    additional_properties: bool = False
    fields: dict[str, str] = Field(default_factory=dict)  # name → file path
    arrays: dict[str, str] = Field(default_factory=dict)  # name → file path
    required_fields: tuple[str, ...] = ()


class ArrayItemsRefList(RootModel[tuple[RefString, ...]]):
    """Reduced form of array items: a list of $ref references.

    YAML shape: [{$ref: a}, {$ref: b}]
    Wraps tuple[RefString, ...] in a typed model for collection safety.
    """

    model_config = ConfigDict(frozen=True)


class RawArray(BaseModel):
    """Array with typed items. Also covers superarrays.

    Items can be:
    - A dict with $ref (single type): {$ref: context_item}
    - A dict with oneOf (union): {oneOf: [{$ref: a}, {$ref: b}]}
    - An ArrayItemsRefList (reduced form): [{$ref: name}]
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: str  # "array"
    description: str | None = None
    items: ArrayItems | ArrayItemsRefList


class RawSection(BaseModel):
    """Section containing fields, sub-components, and arrays.

    Fields are primitive/composed references (same as group fields).
    Sub-components are groups/supergroups referenced by file path.
    Arrays are array references by file path.

    Shallow sections use only fields (flat structure, no nesting).
    Complex sections use fields + sub_components + arrays.
    The name field is the STABLE JSON field name.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: str  # "object"
    description: str | None = None
    composition: str | None = None  # "Mixed"
    additional_properties: bool = False
    required_fields: tuple[str, ...] = ()
    fields: dict[str, str] = Field(default_factory=dict)  # name → file path
    sub_components: dict[str, str] = Field(default_factory=dict)  # name → file path
    arrays: dict[str, str] = Field(default_factory=dict)  # name → file path


class RawSchema(BaseModel):
    """Schema root definition.

    Schemas reference sections by file path in the sections dict.
    The key is the stable JSON field name, the value is the file path.

    Sections with fields support enable shallow sections (flat
    structure without nesting) alongside complex sections with
    sub-components and arrays. Groups dict is retained for
    backward compatibility with existing schemas.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: int
    description: str
    additional_properties: bool = False
    sections: dict[str, str] = Field(default_factory=dict)  # name → file path
    required_sections: tuple[str, ...] = ()
    optional_sections: tuple[str, ...] = ()
    nullable_sections: tuple[str, ...] = ()
    groups: dict[str, str] = Field(default_factory=dict)  # name → group file path
    required_groups: tuple[str, ...] = ()
    nullable_groups: tuple[str, ...] = ()


# =============================================================================
# LOADER INTERFACE (typed callables for the walker — no Any, no unsafe)
# =============================================================================


class SchemaLoaders(BaseModel):
    """Typed loader callables for each composition level.

    Each loader takes a PurePosixPath and returns a validated
    Pydantic model. Validation happens inside the loader (at the
    impure boundary), so the walker never sees untyped data.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    composed: Callable[[PurePosixPath], "RawComposed"]
    group: Callable[[PurePosixPath], "RawGroup"]
    array: Callable[[PurePosixPath], "RawArray"]
    section: Callable[[PurePosixPath], "RawSection"]


# =============================================================================
# WALKED TYPES (after tree walking — Phase 3 walker produces these)
# =============================================================================


class WalkedFields(BaseModel):
    """Intermediate result from walking a fields dict.

    Shared by groups and sections — both have fields dicts with
    the same semantics. The walker classifies each field into one
    of three categories based on its composed type shape.
    """

    model_config = ConfigDict(frozen=True)

    composed_fields: tuple[RawComposed, ...] = ()
    composed_arrays: tuple[RawComposed, ...] = ()
    sub_groups: tuple["WalkedGroup", ...] = ()


class WalkedGroup(BaseModel):
    """Group with its composed fields and sub-structures loaded.

    The walker followed file references and loaded each YAML
    into the appropriate Raw model. This wraps a RawGroup with
    its loaded children.

    source_ref: file path that produced this group (None for synthetic
    groups created from structural composed fields). Used downstream
    by builders to detect reusable groups for $defs emission.
    """

    model_config = ConfigDict(frozen=True)

    raw: RawGroup
    source_ref: str | None = None
    composed_fields: tuple[RawComposed, ...] = ()
    composed_arrays: tuple[RawComposed, ...] = ()  # type="array" composed fields
    sub_groups: tuple["WalkedGroup", ...] = ()  # structural composed → nested groups
    arrays: tuple["WalkedArray", ...] = ()


class WalkedArray(BaseModel):
    """Array with its item types loaded as walked groups."""

    model_config = ConfigDict(frozen=True)

    raw: RawArray
    items: tuple[WalkedGroup, ...]  # resolved item type(s)


class WalkedSection(BaseModel):
    """Section with fields, sub-components, and arrays loaded.

    Fields are processed identically to group fields: thin composed
    become composed_fields, structural composed become sub_groups,
    array-type composed become composed_arrays.
    """

    model_config = ConfigDict(frozen=True)

    raw: RawSection
    composed_fields: tuple[RawComposed, ...] = ()
    composed_arrays: tuple[RawComposed, ...] = ()
    sub_groups: tuple[WalkedGroup, ...] = ()
    components: tuple[WalkedGroup, ...] = ()
    arrays: tuple[WalkedArray, ...] = ()


class WalkedSchema(BaseModel):
    """Full schema tree with all references loaded."""

    model_config = ConfigDict(frozen=True)

    raw: RawSchema
    sections: tuple[WalkedSection, ...] = ()
    groups: tuple[WalkedGroup, ...] = ()
    nullable_sections: tuple[str, ...] = ()
    nullable_groups: tuple[str, ...] = ()


class ForbiddenEntry(BaseModel):
    """A single expanded blocklist entry for inline x-not.

    Each entry carries everything needed to validate a path against it:
    name + (const | enum | pattern) + description.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    const: str | None = None
    enum: tuple[str, ...] | None = None
    pattern: str | None = None
    description: str | None = None


class BlocklistPool(BaseModel):
    """Pre-expanded blocklist entries indexed by composed name.

    Built once at pipeline start from blocklist composed files.
    Passed through resolvers so x-not references expand inline.
    """

    model_config = ConfigDict(frozen=True)

    entries: dict[str, tuple[ForbiddenEntry, ...]] = Field(
        default_factory=dict,
    )


# =============================================================================
# RESOLVED TYPES (after type adoption — Phase 3 resolver produces these)
# =============================================================================


class ResolvedField(BaseModel):
    """A field with its full primitive type chain resolved.

    The resolver walked the type chain (e.g., path_exists_absolute →
    path_allowed_absolute → string) accumulating format, pattern,
    enum, etc. at each level.
    """

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    json_type: str  # terminal type: "string", "integer", "boolean", "array"
    format: str | None = None
    pattern: str | None = None
    enum_values: tuple[str, ...] | None = None
    description: str | None = None
    requirement: str | RequirementCondition | None = None
    const: str | None = None  # fixed value (e.g., return_status)
    default: str | bool | int | None = None
    minimum: int | None = None
    not_entries: tuple[ForbiddenEntry, ...] | None = None  # expanded blocklist
    validation: ValidationConstraint | None = None
    semantic: SemanticConstraint | None = None
    constraint: tuple[ConstraintEntry, ...] | None = None  # resolver hints
    # Array-type primitives (json_type == "array"):
    items_type: str | None = None  # e.g., "string"
    min_items: int | None = None
    max_items: int | None = None
    unique_items: bool | None = None


class ResolvedGroup(BaseModel):
    """Group with all fields resolved to concrete types.

    Covers regular groups, supergroups, and composed structural types.
    Fields are resolved leaf properties. Sub-groups are nested objects
    (from composed structural types). Arrays are resolved array properties.

    source_ref: propagated from WalkedGroup — the YAML file path that
    produced this group. Used by builders to detect shared groups for
    $defs/$ref deduplication.
    """

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    source_ref: str | None = None
    description: str | None = None
    composition: str | None = None
    additional_properties: bool = False
    fields: tuple[ResolvedField, ...] = ()
    sub_groups: tuple["ResolvedGroup", ...] = ()
    arrays: tuple["ResolvedArray", ...] = ()
    required_fields: tuple[str, ...] = ()


class ResolvedArray(BaseModel):
    """Array with resolved item types.

    Items is a union: group-referencing arrays have tuple[ResolvedGroup, ...],
    composed arrays have a single ResolvedField (resolved primitive items).
    """

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    description: str | None = None
    items: tuple[ResolvedGroup, ...] | ResolvedField
    requirement: str | RequirementCondition | None = None  # composed arrays
    min_items: int | None = None
    max_items: int | None = None
    unique_items: bool | None = None
    semantic: SemanticConstraint | None = None
    constraint: tuple[ConstraintEntry, ...] | None = None


class ResolvedSection(BaseModel):
    """Section with fields, sub-components, and arrays fully resolved."""

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    description: str | None = None
    composition: str | None = None
    additional_properties: bool = False
    required_fields: tuple[str, ...] = ()
    fields: tuple[ResolvedField, ...] = ()
    sub_groups: tuple[ResolvedGroup, ...] = ()
    components: tuple[ResolvedGroup, ...] = ()
    arrays: tuple[ResolvedArray, ...] = ()


class ResolvedSchema(BaseModel):
    """Fully resolved schema — ready for JSON Schema building."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: int
    description: str
    additional_properties: bool = False
    required_sections: tuple[str, ...] = ()
    optional_sections: tuple[str, ...] = ()
    nullable_sections: tuple[str, ...] = ()
    sections: tuple[ResolvedSection, ...] = ()
    groups: tuple[ResolvedGroup, ...] = ()
    required_groups: tuple[str, ...] = ()
    nullable_groups: tuple[str, ...] = ()


# =============================================================================
# JSON SCHEMA OUTPUT TYPES (Phase 3 builder produces these)
# =============================================================================
# These model the JSON Schema output format. Each model serializes to the
# correct JSON Schema fragment via model_dump(by_alias=True, exclude_none=True).


class SchemaConst(BaseModel):
    """JSON Schema const constraint: {"const": "value"} or {"const": true}."""

    model_config = ConfigDict(frozen=True)

    const: str | bool


class SchemaEnumConstraint(BaseModel):
    """JSON Schema enum constraint: {"enum": ["a", "b"]}."""

    model_config = ConfigDict(frozen=True)

    enum: tuple[str, ...]


class ConditionProperties(
    RootModel[dict[str, SchemaConst | SchemaEnumConstraint | Literal[False]]],
):
    """JSON Schema properties mapping for condition clauses.

    Keys are field names, values are constraints (const/enum)
    or Literal[False] for prohibition. Wraps dict in a typed
    model for collection safety.
    """

    model_config = ConfigDict(frozen=True)


class SchemaCondition(BaseModel):
    """Body of an if/then/else clause in JSON Schema.

    Used for conditional requirements. The properties values
    are constraints (const/enum) or Literal[False] for prohibition.
    """

    model_config = ConfigDict(frozen=True)

    required: tuple[str, ...] | None = None
    properties: ConditionProperties | None = None


class SchemaConditional(BaseModel):
    """JSON Schema if/then/else conditional construct."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    if_: SchemaCondition = Field(alias="if")
    then_: SchemaCondition = Field(alias="then")
    else_: SchemaCondition | None = Field(default=None, alias="else")


class NestedPathProperties(
    RootModel[
        dict[
            str,
            "SchemaNestedPath | SchemaEnumConstraint | SchemaConst | Literal[False]",
        ]
    ],
):
    """JSON Schema properties mapping for nested path conditionals.

    Self-referential: values can be SchemaNestedPath for further
    nesting, constraints, or Literal[False] for prohibition.
    """

    model_config = ConfigDict(frozen=True)


class SchemaNestedPath(BaseModel):
    """Nested property path for cross-section conditionals.

    Self-referential: each level wraps the next in a properties model.
    Terminal nodes carry either a constraint (enum/const), required
    list, or Literal[False] for prohibition.
    """

    model_config = ConfigDict(frozen=True)

    properties: NestedPathProperties | None = None
    required: tuple[str, ...] | None = None


NestedPathProperties.model_rebuild()
SchemaNestedPath.model_rebuild()


class SchemaRootConditional(BaseModel):
    """Root-level if/then/else for cross-section conditionals.

    Uses SchemaNestedPath bodies (not SchemaCondition) because the
    condition and target span different sections, requiring nested
    property paths to reach the relevant fields.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    if_: SchemaNestedPath = Field(alias="if")
    then_: SchemaNestedPath = Field(alias="then")
    else_: SchemaNestedPath | None = Field(default=None, alias="else")


class SchemaForbiddenEntry(BaseModel):
    """A single forbidden entry in the x-not block."""

    model_config = ConfigDict(frozen=True)

    name: str
    const: str | None = None
    enum: tuple[str, ...] | None = None
    pattern: str | None = None
    description: str | None = None


class SchemaNotBlock(BaseModel):
    """x-not extension with inline forbidden entries."""

    model_config = ConfigDict(frozen=True)

    forbidden: tuple[SchemaForbiddenEntry, ...]


class SchemaSemanticExt(BaseModel):
    """x-semantic extension for quality/semantic checks.

    Uses None (not empty tuple) so exclude_none=True omits absent fields.
    """

    model_config = ConfigDict(frozen=True)

    intent: str
    severity: str
    checks: tuple[str, ...] | None = None
    anti_patterns: tuple[str, ...] | None = None


class SchemaConstraintEntry(BaseModel):
    """A single entry in the x-constraint block."""

    model_config = ConfigDict(frozen=True, extra="allow")

    rule: str
    field: str | None = None
    severity: str
    reason: str


class SchemaConstraintBlock(BaseModel):
    """x-constraint extension with resolver constraint entries."""

    model_config = ConfigDict(frozen=True)

    constraints: tuple[SchemaConstraintEntry, ...]


class SchemaRef(BaseModel):
    """JSON Schema $ref pointer to a $defs entry.

    Emitted by builders when a group appears multiple times in the
    same schema. The first occurrence goes into $defs; subsequent
    occurrences become $ref pointers.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    ref: str = Field(alias="$ref")


class SchemaField(BaseModel):
    """JSON Schema property for a leaf field.

    Serializes to: {type, description?, format?, pattern?, enum?,
    default?, minimum?, x-validation?, x-not?, x-semantic?, x-constraint?}
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str
    description: str | None = None
    const: str | None = None
    format: str | None = None
    pattern: str | None = None
    enum: tuple[str, ...] | None = None
    default: str | bool | int | None = None
    minimum: int | None = None
    x_validation: ValidationConstraint | None = Field(
        default=None, alias="x-validation",
    )
    x_not: SchemaNotBlock | None = Field(default=None, alias="x-not")
    x_semantic: SchemaSemanticExt | None = Field(
        default=None, alias="x-semantic",
    )
    x_constraint: SchemaConstraintBlock | None = Field(
        default=None, alias="x-constraint",
    )


class SchemaObject(BaseModel):
    """JSON Schema object property (groups and sections).

    Serializes to: {type: "object", properties, required?,
    additionalProperties?, allOf?, minProperties?}
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str = "object"
    description: str | None = None
    properties: dict[
        str, "SchemaField | SchemaObject | SchemaArray | SchemaRef"
    ] = Field(default_factory=dict)
    required: tuple[str, ...] | None = None
    additional_properties: bool | None = Field(
        default=None, alias="additionalProperties",
    )
    all_of: tuple[SchemaConditional, ...] | None = Field(
        default=None, alias="allOf",
    )
    min_properties: int | None = Field(
        default=None, alias="minProperties",
    )


class SchemaOneOf(BaseModel):
    """oneOf wrapper for polymorphic array items."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[SchemaObject | SchemaRef, ...] = Field(alias="oneOf")


class SchemaArray(BaseModel):
    """JSON Schema array property.

    Items can be SchemaObject (group), SchemaOneOf (union of groups),
    or SchemaField (composed array with primitive items).
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str = "array"
    description: str | None = None
    items: SchemaObject | SchemaOneOf | SchemaField | SchemaRef
    min_items: int | None = Field(default=None, alias="minItems")
    max_items: int | None = Field(default=None, alias="maxItems")
    unique_items: bool | None = Field(default=None, alias="uniqueItems")
    x_semantic: SchemaSemanticExt | None = Field(
        default=None, alias="x-semantic",
    )
    x_constraint: SchemaConstraintBlock | None = Field(
        default=None, alias="x-constraint",
    )


class SchemaNullType(BaseModel):
    """JSON Schema null type: {"type": "null"}."""

    model_config = ConfigDict(frozen=True)

    type: str = "null"


class SchemaNullableObject(BaseModel):
    """oneOf wrapper for nullable groups: [{properties: ...}, {type: null}].

    Used for root-level groups that can be null (e.g., optional render
    sections like examples, constraints, anti_patterns).
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[SchemaObject, SchemaNullType] = Field(alias="oneOf")
    description: str | None = None


class SchemaDocument(BaseModel):
    """Complete JSON Schema document (root output).

    Serializes to the top-level JSON Schema with $schema, $id, title,
    description, type, required, properties, additionalProperties,
    and optional allOf for cross-section conditionals.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_uri: str = Field(alias="$schema")
    schema_id: str = Field(alias="$id")
    title: str
    description: str
    type: str = "object"
    required: tuple[str, ...] | None = None
    properties: dict[str, SchemaObject | SchemaNullableObject | SchemaRef] = Field(
        default_factory=dict,
    )
    additional_properties: bool | None = Field(
        default=None, alias="additionalProperties",
    )
    defs: dict[str, SchemaObject] | None = Field(
        default=None, alias="$defs",
    )
    all_of: tuple[SchemaRootConditional, ...] | None = Field(
        default=None, alias="allOf",
    )
