"""Tests for draupnir.unsafe.impure.validators — boundary validation."""

import pytest

from draupnir.unsafe.impure.validators import (
    validate_array,
    validate_composed,
    validate_group,
    validate_primitive,
    validate_schema,
    validate_section,
)


class TestValidatePrimitive:
    def test_valid(self) -> None:
        data = {
            "name": "agent_name",
            "type": "string",
            "requirement": "mandatory",
            "description": "Agent identifier.",
        }
        p = validate_primitive(data)
        assert p.name == "agent_name"

    def test_invalid_raises_with_source(self) -> None:
        with pytest.raises(ValueError, match="test.yaml"):
            validate_primitive({"name": "bad"}, source="test.yaml")

    def test_conditional_requirement(self) -> None:
        data = {
            "name": "dispatch_max_agents",
            "type": "integer",
            "minimum": 1,
            "default": 6,
            "requirement": {
                "only_when": {
                    "field": "dispatch_mode",
                    "equals": "batch",
                }
            },
            "description": "Max concurrent agents.",
        }
        p = validate_primitive(data)
        assert not isinstance(p.requirement, str)


class TestValidateComposed:
    def test_thin(self) -> None:
        data = {
            "name": "context_path",
            "type": "path_allowed_any",
            "requirement": "required",
            "description": "Path.",
        }
        c = validate_composed(data)
        assert c.type == "path_allowed_any"

    def test_blocklist(self) -> None:
        data = {
            "name": "PATH_BLOCKLIST",
            "description": "Canonical blocklist.",
            "imports": [
                {"$ref": "path_forbidden_root"},
                {"$ref": "path_forbidden_home"},
            ],
        }
        c = validate_composed(data)
        assert c.imports is not None
        assert len(c.imports) == 2

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            validate_composed({})


class TestValidateGroup:
    def test_valid(self) -> None:
        data = {
            "name": "test_group",
            "type": "object",
            "fields": {"f1": "composed_f1"},
        }
        g = validate_group(data)
        assert g.name == "test_group"


class TestValidateArray:
    def test_single_ref(self) -> None:
        data = {
            "name": "test_array",
            "type": "array",
            "items": {"$ref": "some_item"},
        }
        a = validate_array(data)
        assert a.items.ref == "some_item"

    def test_list_form(self) -> None:
        data = {
            "name": "test_reduced",
            "type": "array",
            "items": [{"$ref": "item_type"}],
        }
        a = validate_array(data)
        assert isinstance(a.items, tuple)
        assert a.items[0].ref == "item_type"


class TestValidateSection:
    def test_valid(self) -> None:
        data = {
            "name": "security",
            "type": "object",
            "sub_components": {"paths": "groups/paths.yaml"},
        }
        s = validate_section(data)
        assert len(s.sub_components) == 1


class TestValidateSchema:
    def test_valid(self) -> None:
        data = {
            "name": "agent-definition",
            "version": 3,
            "description": "Schema.",
            "sections": {"security": "sections/security.yaml"},
            "required_sections": ["security"],
        }
        s = validate_schema(data)
        assert s.version == 3

    def test_invalid_raises_with_source(self) -> None:
        with pytest.raises(ValueError, match="schema.yaml"):
            validate_schema({"name": "bad"}, source="schema.yaml")
