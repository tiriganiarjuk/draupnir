"""Export Pydantic model schemas for Verdandi input validation.

Orchestrate level (CC=1-5). For each Verdandi level, calls
model_json_schema(), parses to typed JsonSchemaNode, applies constraint
encoding and ref-to-string replacement, then serializes and writes through
the JSON writer, which validates each as a JSON Schema document.

Entry point: draupnir-export-schemas → cli.py → run_export()
"""

import sys

from draupnir.logic.impure.paths_locate.primitive import locate_draupnir_paths
from draupnir.logic.impure.writer.ffi import write_json_text
from draupnir.logic.pure.refusal_format.primitive import refusal_text
from draupnir.logic.pure.schema_locate.primitive import (
    input_schema_location,
    json_schema_document_schema,
    schema_file_path,
    verdandi_manifest_schema,
)
from draupnir.logic.transform.schema_export.primitive import manifest_schema_node
from draupnir.logic.transform.schema_export.composed import (
    collect_direct_string_defs,
    collect_union_string_defs,
    encode_constraints,
    replace_string_defs,
)
from draupnir.structure.config.levels import Level
from draupnir.structure.config.schema_export import ExportedSchema, SchemaExportConfig
from draupnir.structure.model.json_schema_node import JsonSchemaNode
from draupnir.structure.model.tool_outcome import ToolRefusal


def export_level_schema(
    level: Level,
    level_names: frozenset[str],
    config: SchemaExportConfig,
) -> JsonSchemaNode:
    """Export and post-process a single level's input schema."""
    model_cls = level.value
    raw_schema = model_cls.model_json_schema()
    schema = JsonSchemaNode.model_validate(raw_schema)
    schema = encode_constraints(schema, config)
    defs = schema.defs or {}
    direct = collect_direct_string_defs(defs, model_cls.__name__, level_names)
    unions = collect_union_string_defs(defs, level_names | direct)
    return replace_string_defs(schema, direct | unions)


def run_export() -> int:
    """Export every level's input schema and the manifest schema.

    Each is written through the JSON writer as a JSON Schema document. A refused
    write stops the export with 1.
    """
    paths = locate_draupnir_paths()
    document_schema = json_schema_document_schema(paths)
    level_names = frozenset(level.value.__name__ for level in Level)
    config = SchemaExportConfig()
    exports = [
        ExportedSchema(
            node=export_level_schema(level, level_names, config),
            path=schema_file_path(input_schema_location(paths, level.name)),
        )
        for level in Level
    ]
    exports.append(ExportedSchema(
        node=manifest_schema_node(),
        path=schema_file_path(verdandi_manifest_schema(paths)),
    ))
    for export in exports:
        text = export.node.model_dump_json(indent=2, by_alias=True, exclude_unset=True)
        outcome = write_json_text(text, export.path, document_schema)
        if isinstance(outcome, ToolRefusal):
            sys.stderr.write(f"WRITE ERROR: {export.path}: {refusal_text(outcome)}\n")
            return 1
        sys.stdout.write(f"wrote {export.path}\n")
    sys.stdout.write(f"\n{len(exports)} schemas exported\n")
    return 0
