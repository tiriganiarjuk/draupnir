"""Tests for draupnir.functions.impure.writers — serialization boundary."""

import json
from pathlib import Path

from draupnir.functions.impure.writers import serialize_schema, write_schema
from draupnir.structures import SchemaDocument, SchemaField, SchemaObject


def _minimal_doc() -> SchemaDocument:
    """Create a minimal SchemaDocument for writer tests."""
    return SchemaDocument(
        schema_uri="https://json-schema.org/draft/2020-12/schema",
        schema_id="agent-test",
        title="test",
        description="Test schema.",
        required=("section_a",),
        properties={
            "section_a": SchemaObject(
                description="Section A.",
                properties={
                    "field_x": SchemaField(
                        type="string", description="Field X.",
                    ),
                },
                required=("field_x",),
            ),
        },
    )


class TestSerializeSchema:
    def test_produces_valid_json(self) -> None:
        text = serialize_schema(_minimal_doc())
        parsed = json.loads(text)
        assert parsed["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert parsed["$id"] == "agent-test"

    def test_aliases_applied(self) -> None:
        text = serialize_schema(_minimal_doc())
        parsed = json.loads(text)
        assert "$schema" in parsed
        assert "$id" in parsed
        assert "schema_uri" not in parsed
        assert "schema_id" not in parsed

    def test_none_excluded(self) -> None:
        text = serialize_schema(_minimal_doc())
        parsed = json.loads(text)
        field = parsed["properties"]["section_a"]["properties"]["field_x"]
        assert "format" not in field
        assert "pattern" not in field
        assert "enum" not in field

    def test_trailing_newline(self) -> None:
        text = serialize_schema(_minimal_doc())
        assert text.endswith("\n")
        assert not text.endswith("\n\n")


class TestWriteSchema:
    def test_creates_file(self, tmp_path: Path) -> None:
        out = tmp_path / "test.schema.json"
        write_schema(_minimal_doc(), out)
        assert out.exists()

    def test_file_content_matches_serialize(self, tmp_path: Path) -> None:
        out = tmp_path / "test.schema.json"
        doc = _minimal_doc()
        write_schema(doc, out)
        assert out.read_text() == serialize_schema(doc)
