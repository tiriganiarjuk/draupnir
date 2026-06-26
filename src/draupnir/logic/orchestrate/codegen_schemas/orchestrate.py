"""Export Pydantic model schemas for Verdandi input validation.

Orchestrate level (CC=1-5). For each of the 15 Verdandi levels, calls
model_json_schema(), parses to typed JsonSchemaNode, applies constraint
encoding and ref-to-string replacement, then serializes and writes.

Entry point: draupnir-export-schemas → cli.py → run_export()
"""

import sys
from pathlib import Path

from draupnir.logic.transform.schema_export.composed import (
    collect_direct_string_defs,
    collect_union_string_defs,
    encode_constraints,
    replace_string_defs,
)
from draupnir.structure.config.levels import Level
from draupnir.structure.config.schema_export import SchemaExportConfig
from draupnir.structure.model.json_schema_node import JsonSchemaNode

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
OUTPUT_DIR = PROJECT_ROOT / "schemas" / "input"


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
    """Export all 15 level input schemas."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    level_names = frozenset(level.value.__name__ for level in Level)
    config = SchemaExportConfig()
    count = 0
    for level in Level:
        schema = export_level_schema(level, level_names, config)
        output_path = OUTPUT_DIR / f"{level.name}.schema.json"
        serialized = schema.model_dump_json(indent=2, by_alias=True, exclude_unset=True)
        output_path.write_text(serialized + "\n")
        sys.stdout.write(f"wrote {output_path.name}\n")
        count += 1
    sys.stdout.write(f"\n{count} schemas exported to {OUTPUT_DIR}\n")
    return 0
