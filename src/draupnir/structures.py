"""Frozen Pydantic models for the Draupnir schema generator.

All models are frozen (immutable) and contain NO methods.
All logic lives in standalone functions in other modules.

YAML shape matching: Raw models mirror the YAML structure exactly so that
Model.model_validate(yaml_dict) works directly. Pydantic aliases handle
YAML keys that aren't valid Python identifiers (e.g., $ref, not).
"""

from pydantic import BaseModel, ConfigDict, Field


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


class ConditionalRequirement(BaseModel):
    """Conditional requirement — field required only when another field matches.

    YAML shape: {only_when: {field: str, equals?: str, in?: [str], present?: bool}}
    """

    model_config = ConfigDict(frozen=True)

    field: str
    equals: str | None = None
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


class RawComposed(BaseModel):
    """Composed field as loaded from YAML.

    Three shapes:
    - Thin: adopts a primitive type (type = primitive name).
    - Structural: an object with its own fields (type = "object").
    - Blocklist: pattern composition (imports list of $refs, no type field).

    Requirement can be string or conditional dict.
    The name field is the STABLE JSON field name — never changes per stage.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: str | None = None  # primitive name, "object", or absent (blocklist)
    requirement: str | RequirementCondition | None = None
    description: str | None = None
    # Structural composed only (type == "object"):
    composition: str | None = None  # "AllOf", "OneOf"
    additional_properties: bool | None = None
    fields: dict[str, str] | None = None  # field_name → primitive type name
    # Blocklist pattern (no type field):
    imports: tuple[RefString, ...] | None = None


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


class RawArray(BaseModel):
    """Array with typed items. Also covers superarrays.

    Items can be:
    - A dict with $ref (single type): {$ref: context_item}
    - A dict with oneOf (union): {oneOf: [{$ref: a}, {$ref: b}]}
    - A list of $ref dicts (reduced form): [{$ref: name}]
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: str  # "array"
    description: str | None = None
    items: ArrayItems | tuple[RefString, ...]


class RawSection(BaseModel):
    """Section containing sub-components (groups and supergroups).

    Sub-components are referenced by file path.
    The name field is the STABLE JSON field name.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: str  # "object"
    description: str | None = None
    composition: str | None = None  # "Mixed"
    additional_properties: bool = False
    required_fields: tuple[str, ...] = ()
    sub_components: dict[str, str] = Field(default_factory=dict)  # name → file path


class RawSchema(BaseModel):
    """Schema root definition.

    After YAML migration (Phase 5), schemas reference sections
    by file path in the sections dict. The key is the stable JSON
    field name, the value is the section file path.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: int
    description: str
    additional_properties: bool = False
    sections: dict[str, str] = Field(default_factory=dict)  # name → file path
    required_sections: tuple[str, ...] = ()
    optional_sections: tuple[str, ...] = ()


# =============================================================================
# WALKED TYPES (after tree walking — Phase 3 walker produces these)
# =============================================================================


class WalkedGroup(BaseModel):
    """Group with its composed fields and sub-structures loaded.

    The walker followed file references and loaded each YAML
    into the appropriate Raw model. This wraps a RawGroup with
    its loaded children.
    """

    model_config = ConfigDict(frozen=True)

    raw: RawGroup
    composed_fields: tuple[RawComposed, ...] = ()
    sub_groups: tuple["WalkedGroup", ...] = ()  # structural composed → nested groups
    arrays: tuple["WalkedArray", ...] = ()


class WalkedArray(BaseModel):
    """Array with its item types loaded as walked groups."""

    model_config = ConfigDict(frozen=True)

    raw: RawArray
    items: tuple[WalkedGroup, ...]  # resolved item type(s)


class WalkedSection(BaseModel):
    """Section with all sub-components loaded as walked groups."""

    model_config = ConfigDict(frozen=True)

    raw: RawSection
    components: tuple[WalkedGroup, ...] = ()


class WalkedSchema(BaseModel):
    """Full schema tree with all references loaded."""

    model_config = ConfigDict(frozen=True)

    raw: RawSchema
    sections: tuple[WalkedSection, ...] = ()


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
    json_type: str  # terminal type: "string", "integer", "boolean"
    format: str | None = None
    pattern: str | None = None
    enum_values: tuple[str, ...] | None = None
    description: str | None = None
    requirement: str | None = None
    default: str | bool | int | None = None
    minimum: int | None = None
    not_ref: str | None = None  # blocklist reference name
    validation: ValidationConstraint | None = None
    semantic: SemanticConstraint | None = None


class ResolvedGroup(BaseModel):
    """Group with all fields resolved to concrete types.

    Covers regular groups, supergroups, and composed structural types.
    Fields are resolved leaf properties. Sub-groups are nested objects
    (from composed structural types). Arrays are resolved array properties.
    """

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    description: str | None = None
    composition: str | None = None
    additional_properties: bool = False
    fields: tuple[ResolvedField, ...] = ()
    sub_groups: tuple["ResolvedGroup", ...] = ()
    arrays: tuple["ResolvedArray", ...] = ()
    required_fields: tuple[str, ...] = ()


class ResolvedArray(BaseModel):
    """Array with resolved item types."""

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    description: str | None = None
    items: tuple[ResolvedGroup, ...]  # one = single type, multiple = oneOf


class ResolvedSection(BaseModel):
    """Section with all sub-components fully resolved."""

    model_config = ConfigDict(frozen=True)

    name: str  # STABLE JSON field name
    description: str | None = None
    composition: str | None = None
    additional_properties: bool = False
    required_fields: tuple[str, ...] = ()
    components: tuple[ResolvedGroup, ...] = ()


class ResolvedSchema(BaseModel):
    """Fully resolved schema — ready for JSON Schema building."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: int
    description: str
    additional_properties: bool = False
    required_sections: tuple[str, ...] = ()
    optional_sections: tuple[str, ...] = ()
    sections: tuple[ResolvedSection, ...] = ()
