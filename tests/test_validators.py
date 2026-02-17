"""Tests for draupnir.functions.impure.loaders — boundary validation.

These test the validation behavior (valid data → model, invalid data → error)
using Pydantic model_validate directly, since the loaders combine IO + validation.
Integration tests cover the full load-from-file path.
"""

import pytest

from pydantic import ValidationError

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSchema,
    RawSection,
)


class TestValidatePrimitive:
    def test_valid(self) -> None:
        data = {
            "name": "agent_name",
            "type": "string",
            "requirement": "mandatory",
            "description": "Agent identifier.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.name == "agent_name"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawPrimitive.model_validate({"name": "bad"})

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
        p = RawPrimitive.model_validate(data)
        assert not isinstance(p.requirement, str)


class TestValidateComposed:
    def test_thin(self) -> None:
        data = {
            "name": "context_path",
            "type": "path_allowed_any",
            "requirement": "required",
            "description": "Path.",
        }
        c = RawComposed.model_validate(data)
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
        c = RawComposed.model_validate(data)
        assert c.imports is not None
        assert len(c.imports) == 2

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawComposed.model_validate({})


class TestValidateGroup:
    def test_valid(self) -> None:
        data = {
            "name": "test_group",
            "type": "object",
            "fields": {"f1": "composed_f1"},
        }
        g = RawGroup.model_validate(data)
        assert g.name == "test_group"


class TestValidateArray:
    def test_single_ref(self) -> None:
        data = {
            "name": "test_array",
            "type": "array",
            "items": {"$ref": "some_item"},
        }
        a = RawArray.model_validate(data)
        assert a.items.ref == "some_item"

    def test_list_form(self) -> None:
        data = {
            "name": "test_reduced",
            "type": "array",
            "items": [{"$ref": "item_type"}],
        }
        a = RawArray.model_validate(data)
        assert isinstance(a.items, tuple)
        assert a.items[0].ref == "item_type"


class TestValidateSection:
    def test_valid(self) -> None:
        data = {
            "name": "security",
            "type": "object",
            "sub_components": {"paths": "groups/paths.yaml"},
        }
        s = RawSection.model_validate(data)
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
        s = RawSchema.model_validate(data)
        assert s.version == 3

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValidationError):
            RawSchema.model_validate({"name": "bad"})
