"""Typed representation of a JSON Schema node for export post-processing.

Captures the fields that export transforms access while preserving all
other fields via extra="allow". Recursive — $defs values, properties
values, and anyOf/oneOf branches are all JsonSchemaNode.

Used by the codegen_schemas pipeline to replace dict[str, Any] with
typed operations on model_json_schema() output.
"""

from pydantic import BaseModel, ConfigDict, Field


class JsonSchemaNode(BaseModel):
    """Minimal typed JSON Schema node.

    extra="allow" preserves fields this model doesn't declare (pattern,
    min_length, items, additionalProperties, etc.) through round-trip
    serialization. Only fields accessed by the export transforms are
    declared explicitly.
    """

    model_config = ConfigDict(frozen=True, extra="allow", populate_by_name=True)

    title: str | None = None
    type: str | None = None
    description: str | None = None
    ref: str | None = Field(None, alias="$ref")
    defs: dict[str, "JsonSchemaNode"] | None = Field(None, alias="$defs")
    properties: dict[str, "JsonSchemaNode"] | None = None
    required: list[str] | None = None
    any_of: list["JsonSchemaNode"] | None = Field(None, alias="anyOf")
    one_of: list["JsonSchemaNode"] | None = Field(None, alias="oneOf")
    enum: list[str] | None = None
    const: bool | str | int | None = None
