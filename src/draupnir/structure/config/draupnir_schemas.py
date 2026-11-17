"""The schemas Draupnir keeps for its own files, by the name the Nornir tools take.

Each default is a file name under schemas/config/ without .schema.json. Callers
pass these fields, so no schema name is written anywhere else.
"""

from pydantic import BaseModel, ConfigDict


class DraupnirSchemas(BaseModel):
    """Names of the schemas Draupnir validates its own reads and writes against."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    json_schema_document: str = "json-schema-document"
    codegen_input: str = "codegen-input"
    verdandi_manifest: str = "verdandi-manifest"
