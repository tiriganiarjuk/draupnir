"""End-to-end tests: YAML fixtures → pipeline → JSON Schema output."""

import json
from pathlib import Path

import pytest

from draupnir.functions.impure.writers import serialize_schema, write_schema
from draupnir.functions.impure.pipeline import generate_all_schemas, generate_schema

FIXTURES = Path(__file__).parent / "fixtures" / "toolcompose"


class TestGenerateSchema:
    def test_produces_schema_document(self) -> None:
        """Pipeline produces a SchemaDocument from fixtures."""
        schema_path = FIXTURES / "schema" / "test-schema.yaml"
        doc = generate_schema(schema_path, FIXTURES)
        assert doc.title == "test-schema"
        assert doc.schema_uri == "https://json-schema.org/draft/2020-12/schema"
        assert doc.schema_id == "agent-test-schema"

    def test_output_structure(self) -> None:
        """Generated document has expected JSON Schema structure."""
        schema_path = FIXTURES / "schema" / "test-schema.yaml"
        doc = generate_schema(schema_path, FIXTURES)
        assert doc.type == "object"
        assert doc.required == ("security",)
        assert "security" in doc.properties
        security = doc.properties["security"]
        assert "paths" in security.properties
        assert "entries" in security.properties

    def test_field_properties_resolved(self) -> None:
        """Fields carry resolved primitive properties (pattern, format)."""
        schema_path = FIXTURES / "schema" / "test-schema.yaml"
        doc = generate_schema(schema_path, FIXTURES)
        security = doc.properties["security"]
        paths = security.properties["paths"]
        workspace = paths.properties["workspace"]
        assert workspace.type == "string"
        assert workspace.format == "uri-reference"

    def test_array_items_resolved(self) -> None:
        """Array items reference groups correctly."""
        schema_path = FIXTURES / "schema" / "test-schema.yaml"
        doc = generate_schema(schema_path, FIXTURES)
        security = doc.properties["security"]
        entries = security.properties["entries"]
        assert entries.type == "array"
        assert "agent_name" in entries.items.properties


class TestSerializeSchema:
    def test_serialize_roundtrip(self) -> None:
        """Serialized JSON parses back to valid structure."""
        schema_path = FIXTURES / "schema" / "test-schema.yaml"
        doc = generate_schema(schema_path, FIXTURES)
        json_text = serialize_schema(doc)
        parsed = json.loads(json_text)
        assert parsed["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert parsed["$id"] == "agent-test-schema"
        assert parsed["title"] == "test-schema"
        assert parsed["type"] == "object"


class TestWriteSchema:
    def test_write_and_read_back(self, tmp_path: Path) -> None:
        """Written file reads back as valid JSON Schema."""
        schema_path = FIXTURES / "schema" / "test-schema.yaml"
        doc = generate_schema(schema_path, FIXTURES)
        out_file = tmp_path / "test.schema.json"
        write_schema(doc, out_file)
        assert out_file.exists()
        parsed = json.loads(out_file.read_text())
        assert parsed["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "properties" in parsed


class TestGenerateAllSchemas:
    def test_discovers_and_generates(self) -> None:
        """generate_all_schemas finds fixture schema and generates it."""
        results = generate_all_schemas(FIXTURES)
        assert len(results) == 1
        assert "test-schema" in results
        doc = results["test-schema"]
        assert doc.title == "test-schema"

    def test_missing_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty dict."""
        results = generate_all_schemas(tmp_path)
        assert results == {}
