#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = ["pydantic>=2.0", "pyyaml>=6.0"]
# ///
"""Export Pydantic model schemas for Verdandi input validation.

For each of the 15 Verdandi levels, exports a JSON Schema that describes
the raw YAML input shape. Ref fields (references to other YAML files)
are replaced with {"type": "string"} since they are cache key strings
in the YAML, not nested objects.

Usage: ./tools/export_input_schemas.py
"""

import json
import sys
from pathlib import Path
from typing import Any

# Add draupnir src to path so we can import the models
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from draupnir.structure.config.levels import Level

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "schemas" / "input"

# All Level model class names — these are separate YAML files,
# so their refs are strings in the raw YAML input.
LEVEL_MODEL_NAMES = frozenset(level.value.__name__ for level in Level)


def is_level_ref(def_name: str, def_schema: dict[str, Any], exclude: str) -> bool:
    """Check if a $defs entry represents a Level model (separate YAML file).

    Excludes the model being exported — it is not a ref to itself.
    """
    if def_name == exclude:
        return False
    if def_name in LEVEL_MODEL_NAMES:
        return True
    return False


def is_union_of_level_refs(def_schema: dict[str, Any], level_names: frozenset[str]) -> bool:
    """Check if a $defs entry is an anyOf union where all branches are Level model $refs."""
    any_of = def_schema.get("anyOf")
    if not any_of:
        return False
    for branch in any_of:
        ref_path = branch.get("$ref", "")
        if ref_path.startswith("#/$defs/"):
            ref_name = ref_path.split("/")[-1]
            if ref_name not in level_names:
                return False
        else:
            return False
    return True


def is_copy_of_level_model(def_schema: dict[str, Any]) -> bool:
    """Check if a $defs entry is a full copy of a Level model (same title)."""
    title = def_schema.get("title")
    return title is not None and title in LEVEL_MODEL_NAMES


def collect_string_defs(schema: dict[str, Any], exclude: str) -> set[str]:
    """Identify $defs entries that should become {"type": "string"}.

    Three cases:
    1. The entry IS a Level model (its name matches a Level class name)
    2. The entry is an anyOf union where all branches $ref Level models
    3. The entry is a full copy of a Level model (title matches a Level class name)

    Excludes the model being exported — it is not a ref to itself.
    """
    defs = schema.get("$defs", {})
    string_defs: set[str] = set()

    for def_name, def_schema in defs.items():
        if is_level_ref(def_name, def_schema, exclude):
            string_defs.add(def_name)
        elif def_name != exclude and is_copy_of_level_model(def_schema):
            string_defs.add(def_name)

    # Second pass: unions of level refs (and refs to already-stringified defs)
    all_string_names = LEVEL_MODEL_NAMES | string_defs
    for def_name, def_schema in defs.items():
        if def_name not in string_defs and is_union_of_level_refs(def_schema, all_string_names):
            string_defs.add(def_name)

    return string_defs


def replace_string_defs(schema: dict[str, Any], string_defs: set[str]) -> dict[str, Any]:
    """Replace identified $defs entries with {"type": "string"}."""
    defs = schema.get("$defs", {})
    for def_name in string_defs:
        defs[def_name] = {"type": "string"}
    return schema


EXACTLY_ONE_CONDITION_MODELS = frozenset({
    "SimplegroupConditionalEntry",
    "GroupFieldConditionalEntry",
    "GroupContainerConditionalEntry",
    "SectionContainerConditionalEntry",
    "ShallowFieldConditionalEntry",
    "ShallowContainerConditionalEntry",
    "SchemaSectionConditionalEntry",
    "SchemaShallowConditionalEntry",
})

AT_LEAST_ONE_ZONE_MODELS = frozenset({
    "Simplegroup",
    "Group",
})


def add_exactly_one_constraint(
    def_schema: dict[str, Any],
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    """Add oneOf constraint: exactly one of the given fields must be present."""
    def_schema["oneOf"] = [{"required": [name]} for name in field_names]
    return def_schema


def add_at_least_one_constraint(
    def_schema: dict[str, Any],
    field_names: tuple[str, ...],
) -> dict[str, Any]:
    """Add anyOf constraint: at least one of the given fields must be present."""
    def_schema["anyOf"] = [{"required": [name]} for name in field_names]
    return def_schema


def encode_constraints(schema: dict[str, Any]) -> dict[str, Any]:
    """Encode model validator constraints as JSON Schema constructs.

    Replaces @model_validator logic with declarative JSON Schema
    so the gate enforces these constraints at validation time.
    """
    defs = schema.get("$defs", {})

    for def_name, def_schema in defs.items():
        if def_name == "ConditionalWhen":
            # exactly one of equals/in_/exists, and exists must be true
            add_exactly_one_constraint(def_schema, ("equals", "in", "exists"))
            properties = def_schema.get("properties", {})
            if "exists" in properties:
                properties["exists"] = {"const": True}

        elif def_name in EXACTLY_ONE_CONDITION_MODELS:
            add_exactly_one_constraint(
                def_schema, ("only_when", "always_when", "not_when"),
            )

        elif def_name in AT_LEAST_ONE_ZONE_MODELS:
            zone_fields = []
            for field_name in ("required", "optional", "conditional",
                               "fields", "containers"):
                if field_name in def_schema.get("properties", {}):
                    zone_fields.append(field_name)
            add_at_least_one_constraint(def_schema, tuple(zone_fields))

    # Schema root: exactly one of sections/shallowsections
    root_ref = schema.get("$ref", "")
    if root_ref == "#/$defs/Schema":
        schema_def = defs.get("Schema", {})
        add_exactly_one_constraint(schema_def, ("sections", "shallowsections"))

    return schema


def export_level_schema(level: Level) -> dict[str, Any]:
    """Export and post-process a single level's input schema."""
    model_cls = level.value
    schema = model_cls.model_json_schema()
    encode_constraints(schema)
    string_defs = collect_string_defs(schema, model_cls.__name__)
    replace_string_defs(schema, string_defs)
    return schema


def main() -> int:
    """Export all 15 level input schemas."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for level in Level:
        schema = export_level_schema(level)
        output_path = OUTPUT_DIR / f"{level.name}.schema.json"
        output_path.write_text(json.dumps(schema, indent=2) + "\n")
        sys.stdout.write(f"wrote {output_path.name}\n")
        count += 1
    sys.stdout.write(f"\n{count} schemas exported to {OUTPUT_DIR}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
