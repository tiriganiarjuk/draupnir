"""JSON Schema output models — the builder produces these.

Each model serializes to a correct JSON Schema fragment via
model_dump(by_alias=True, exclude_none=True). These model the
OUTPUT format (JSON Schema), not the INPUT format (Verdandi YAML).

Ported from recyclable_structures_consume_and_destroy.py with
additions for Verdandi constructs (tuples as prefixItems, unions
as oneOf fields).
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


# --- Leaf constraints ---


class SchemaConst(BaseModel):
    """JSON Schema const constraint: {"const": "value"}."""

    model_config = ConfigDict(frozen=True)

    const: str | int | bool


class SchemaEnumConstraint(BaseModel):
    """JSON Schema enum constraint: {"enum": ["a", "b"]}."""

    model_config = ConfigDict(frozen=True)

    enum: tuple[str | int | bool, ...]


class SchemaPatternConstraint(BaseModel):
    """Pattern-only schema fragment for not/anyOf constructs."""

    model_config = ConfigDict(frozen=True)

    pattern: str


class SchemaAnyOfConstraint(BaseModel):
    """anyOf wrapper for multiple pattern exclusions in not blocks."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    any_of: tuple[SchemaPatternConstraint, ...] = Field(alias="anyOf")


class ValidationConstraint(BaseModel):
    """x-validation extension for runtime validation hints."""

    model_config = ConfigDict(frozen=True)

    instruction: str
    severity: str


# --- Conditional constructs ---


class ConditionProperties(
    RootModel[dict[str, SchemaConst | SchemaEnumConstraint | Literal[False]]],
):
    """Properties mapping for condition clauses.

    Keys are field names, values are constraints (const/enum)
    or Literal[False] for prohibition.
    """

    model_config = ConfigDict(frozen=True)


class SchemaCondition(BaseModel):
    """Body of an if/then/else clause in JSON Schema."""

    model_config = ConfigDict(frozen=True)

    required: tuple[str, ...] | None = None
    properties: ConditionProperties | None = None


class SchemaConditional(BaseModel):
    """JSON Schema if/then/else conditional construct."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    if_: SchemaCondition = Field(alias="if")
    then_: SchemaCondition = Field(alias="then")
    else_: SchemaCondition | None = Field(default=None, alias="else")


# --- Nested path conditionals (cross-section) ---


class NestedPathProperties(
    RootModel[
        dict[
            str,
            "SchemaNestedPath | SchemaEnumConstraint | SchemaConst | Literal[False]",
        ]
    ],
):
    """Properties mapping for nested path conditionals.

    Self-referential: values can be SchemaNestedPath for further
    nesting, constraints, or Literal[False] for prohibition.
    """

    model_config = ConfigDict(frozen=True)


class SchemaNestedPath(BaseModel):
    """Nested property path for cross-section conditionals.

    Self-referential: each level wraps the next in a properties model.
    """

    model_config = ConfigDict(frozen=True)

    properties: NestedPathProperties | None = None
    required: tuple[str, ...] | None = None


NestedPathProperties.model_rebuild()
SchemaNestedPath.model_rebuild()


class SchemaRootConditional(BaseModel):
    """Root-level if/then/else for cross-section conditionals.

    Uses SchemaNestedPath bodies because conditions span sections.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    if_: SchemaNestedPath = Field(alias="if")
    then_: SchemaNestedPath = Field(alias="then")
    else_: SchemaNestedPath | None = Field(default=None, alias="else")


# --- Extension blocks ---


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
    """x-semantic extension for quality/semantic checks."""

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


# --- Schema $ref ---


class SchemaRef(BaseModel):
    """JSON Schema $ref pointer to a $defs entry."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    ref: str = Field(alias="$ref")


# --- Core output types ---


class SchemaField(BaseModel):
    """JSON Schema property for a leaf field."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str
    description: str | None = None
    const: str | None = None
    format: str | None = None
    pattern: str | None = None
    enum: tuple[str | int | bool, ...] | None = None
    default: str | bool | int | None = None
    minimum: int | None = None
    not_: SchemaPatternConstraint | SchemaAnyOfConstraint | None = Field(
        default=None,
        alias="not",
    )
    x_validation: ValidationConstraint | None = Field(
        default=None,
        alias="x-validation",
    )
    x_not: SchemaNotBlock | None = Field(default=None, alias="x-not")
    x_semantic: SchemaSemanticExt | None = Field(
        default=None,
        alias="x-semantic",
    )
    x_constraint: SchemaConstraintBlock | None = Field(
        default=None,
        alias="x-constraint",
    )


class SchemaOneOfField(BaseModel):
    """oneOf wrapper for union fields (Verdandi union → JSON Schema oneOf)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[SchemaField | SchemaRef, ...] = Field(alias="oneOf")
    description: str | None = None


class SchemaObject(BaseModel):
    """JSON Schema object property (groups and sections)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str = "object"
    description: str | None = None
    properties: dict[
        str,
        "SchemaField | SchemaOneOfField | SchemaObject | SchemaArray | SchemaTupleArray | SchemaRef",
    ] = Field(default_factory=dict)
    required: tuple[str, ...] | None = None
    additional_properties: bool | None = Field(
        default=None,
        alias="additionalProperties",
    )
    all_of: tuple[SchemaConditional, ...] | None = Field(
        default=None,
        alias="allOf",
    )
    min_properties: int | None = Field(
        default=None,
        alias="minProperties",
    )


class SchemaOneOf(BaseModel):
    """oneOf wrapper for polymorphic array items."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[SchemaObject | SchemaRef, ...] = Field(alias="oneOf")


class SchemaArray(BaseModel):
    """JSON Schema array property.

    Items can be SchemaObject (group), SchemaOneOf (union of groups),
    SchemaField (primitive items), or SchemaRef ($ref).
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str = "array"
    description: str | None = None
    items: "SchemaObject | SchemaOneOf | SchemaField | SchemaOneOfField | SchemaRef"
    min_items: int | None = Field(default=None, alias="minItems")
    max_items: int | None = Field(default=None, alias="maxItems")
    unique_items: bool | None = Field(default=None, alias="uniqueItems")
    x_semantic: SchemaSemanticExt | None = Field(
        default=None,
        alias="x-semantic",
    )
    x_constraint: SchemaConstraintBlock | None = Field(
        default=None,
        alias="x-constraint",
    )


class SchemaTupleArray(BaseModel):
    """JSON Schema tuple array (Verdandi tuple → prefixItems + items: false)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    type: str = "array"
    description: str | None = None
    prefix_items: tuple[SchemaField | SchemaRef, ...] = Field(alias="prefixItems")
    items: Literal[False] = False
    min_items: int | None = Field(default=None, alias="minItems")
    max_items: int | None = Field(default=None, alias="maxItems")


# Rebuild forward refs for SchemaObject.properties
SchemaObject.model_rebuild()


# --- Nullable ---


class SchemaNullType(BaseModel):
    """JSON Schema null type: {"type": "null"}."""

    model_config = ConfigDict(frozen=True)

    type: str = "null"


class SchemaNullableObject(BaseModel):
    """oneOf wrapper for nullable groups: [{...}, {type: null}]."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    one_of: tuple[SchemaObject, SchemaNullType] = Field(alias="oneOf")
    description: str | None = None


# --- Root document ---


class SchemaDocument(BaseModel):
    """Complete JSON Schema document (root output)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    schema_uri: str = Field(alias="$schema")
    schema_id: str = Field(alias="$id")
    title: str
    description: str
    type: str = "object"
    required: tuple[str, ...] | None = None
    properties: dict[
        str, SchemaObject | SchemaNullableObject | SchemaRef
    ] = Field(default_factory=dict)
    additional_properties: bool | None = Field(
        default=None,
        alias="additionalProperties",
    )
    defs: dict[
        str,
        SchemaObject | SchemaArray | SchemaTupleArray | SchemaField | SchemaOneOfField,
    ] | None = Field(
        default=None,
        alias="$defs",
    )
    all_of: tuple[SchemaRootConditional, ...] | None = Field(
        default=None,
        alias="allOf",
    )
