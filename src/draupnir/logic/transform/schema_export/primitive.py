"""Schema export primitives — a model's JSON Schema as a node.

CC=1. The level input schemas are authored, not exported; what is exported
from a model is the manifest schema.
"""

from draupnir.structure.config.verdandi_manifest import VerdandiManifest
from draupnir.structure.model.json_schema_node import JsonSchemaNode


def manifest_schema_node() -> JsonSchemaNode:
    """The manifest's schema, exported from the VerdandiManifest model it validates."""
    return JsonSchemaNode.model_validate(VerdandiManifest.model_json_schema())
