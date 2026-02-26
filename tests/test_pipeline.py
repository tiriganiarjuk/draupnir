"""E2E pipeline tests — load real Verdandi YAML, export, validate output.

Tests the full pipeline: loader → exporter → writer against the actual
Verdandi YAML files. This is the integration gate for Phase 8.
"""

import json
from pathlib import Path

import jsonschema
import pytest
from pydantic import BaseModel

from draupnir.functions.impure.loader import load_all_levels
from draupnir.functions.impure.pipeline import resolve_paths, schema_filename
from draupnir.functions.impure.writer import serialize_schema
from draupnir.functions.pure.exporter import export_all_schemas


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
VERDANDI_ROOT = WORKSPACE_ROOT / "tools" / "verdandi"
SCHEMA_OUTPUT_DIR = WORKSPACE_ROOT / "schemas"

EXPECTED_SCHEMA_COUNT = 12


@pytest.fixture(scope="module")
def loaded_cache():
    """Load all Verdandi YAML into cache — shared across module."""
    cache: dict[str, BaseModel] = {}
    load_all_levels(VERDANDI_ROOT, cache)
    return cache


@pytest.fixture(scope="module")
def exported_schemas(loaded_cache):
    """Export all schemas from cache — shared across module."""
    return export_all_schemas(loaded_cache)


# --- Loader tests ---


class TestLoader:
    def test_cache_not_empty(self, loaded_cache):
        assert len(loaded_cache) > 100

    def test_all_levels_represented(self, loaded_cache):
        levels_found = {key.split("/")[0] for key in loaded_cache}
        expected = {
            "pattern", "enum", "atom", "element", "union",
            "tuple", "simplearray", "simplegroup",
            "array", "group", "superarray",
            "section", "shallowsection", "schema",
        }
        assert expected == levels_found

    def test_schema_count(self, loaded_cache):
        schemas = [k for k in loaded_cache if k.startswith("schema/")]
        assert len(schemas) == EXPECTED_SCHEMA_COUNT


# --- Exporter tests ---


class TestExporter:
    def test_produces_expected_count(self, exported_schemas):
        assert len(exported_schemas) == EXPECTED_SCHEMA_COUNT

    def test_all_have_properties(self, exported_schemas):
        for key, document in exported_schemas.items():
            assert len(document.properties) > 0, f"{key} has no properties"

    def test_all_have_description(self, exported_schemas):
        for key, document in exported_schemas.items():
            assert document.description, f"{key} has no description"


# --- Serialization tests ---


class TestSerialization:
    def test_serialize_produces_valid_json(self, exported_schemas):
        for key, document in exported_schemas.items():
            text = serialize_schema(document)
            parsed = json.loads(text)
            assert "$schema" in parsed, f"{key} missing $schema"
            assert "$id" in parsed, f"{key} missing $id"
            assert "properties" in parsed, f"{key} missing properties"

    def test_aliases_applied(self, exported_schemas):
        """Verify Pydantic aliases produce correct JSON Schema keys."""
        for key, document in exported_schemas.items():
            text = serialize_schema(document)
            parsed = json.loads(text)
            assert "additionalProperties" in parsed, f"{key} missing additionalProperties"
            if parsed.get("$defs"):
                assert "$defs" in parsed

    def test_none_fields_excluded(self, exported_schemas):
        """Verify exclude_none drops null fields from output."""
        for key, document in exported_schemas.items():
            text = serialize_schema(document)
            assert '"allOf": null' not in text


# --- JSON Schema meta-validation ---


class TestMetaValidation:
    def test_each_schema_is_valid_json_schema(self, exported_schemas):
        """Validate each generated schema against JSON Schema Draft 2020-12."""
        for key, document in exported_schemas.items():
            text = serialize_schema(document)
            parsed = json.loads(text)
            jsonschema.Draft202012Validator.check_schema(parsed)

    def test_defs_refs_resolve(self, exported_schemas):
        """Verify every $ref in schemas points to an existing $defs entry."""
        for key, document in exported_schemas.items():
            text = serialize_schema(document)
            parsed = json.loads(text)
            defs = parsed.get("$defs", {})
            refs = find_all_refs(parsed)
            for ref_path in refs:
                def_name = ref_path.split("/")[-1]
                assert def_name in defs, f"{key}: $ref {ref_path} not in $defs"


# --- Pipeline utility tests ---


class TestPipelineUtils:
    def test_schema_filename(self):
        assert schema_filename("schema/agent-raw-definition") == "agent-raw-definition.schema.json"
        assert schema_filename("schema/agent-universal-format") == "agent-universal-format.schema.json"

    def test_resolve_paths_defaults(self):
        verdandi, output = resolve_paths(None, None, WORKSPACE_ROOT)
        assert verdandi == VERDANDI_ROOT
        assert output == SCHEMA_OUTPUT_DIR


# --- On-disk consistency ---


class TestDiskConsistency:
    def test_generated_matches_ondisk(self, exported_schemas):
        """Verify freshly exported schemas match what's on disk."""
        for key, document in exported_schemas.items():
            fname = schema_filename(key)
            disk_path = SCHEMA_OUTPUT_DIR / fname
            if not disk_path.exists():
                pytest.skip(f"{fname} not on disk yet")
            fresh = json.loads(serialize_schema(document))
            ondisk = json.loads(disk_path.read_text())
            assert fresh == ondisk, f"{fname} differs from on-disk version"


# --- Helpers ---


def find_all_refs(data: dict | list | str | int | bool | None) -> list[str]:
    """Recursively find all $ref values in a JSON structure."""
    refs: list[str] = []
    if isinstance(data, dict):
        if "$ref" in data:
            refs.append(data["$ref"])
        for value in data.values():
            refs.extend(find_all_refs(value))
    elif isinstance(data, list):
        for item in data:
            refs.extend(find_all_refs(item))
    return refs
