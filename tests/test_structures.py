"""Tests for draupnir.structures — frozen Pydantic models.

Focus: models match YAML shapes so model_validate(yaml_dict) works directly.
"""

import pytest
from pydantic import ValidationError

from draupnir.structures import (
    ArrayItems,
    NotConstraint,
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSchema,
    RawSection,
    RefString,
    ResolvedArray,
    ResolvedField,
    ResolvedGroup,
    ResolvedSchema,
    ResolvedSection,
    SemanticConstraint,
    ValidationConstraint,
    WalkedArray,
    WalkedGroup,
    WalkedSchema,
    WalkedSection,
)


# =============================================================================
# SUB-STRUCTURE MODELS
# =============================================================================


class TestValidationConstraint:
    def test_create(self) -> None:
        v = ValidationConstraint(instruction="Must exist.", severity="error")
        assert v.instruction == "Must exist."
        assert v.severity == "error"

    def test_from_yaml_dict(self) -> None:
        data = {"instruction": "Must exist on filesystem.", "severity": "error"}
        v = ValidationConstraint.model_validate(data)
        assert v.severity == "error"

    def test_frozen(self) -> None:
        v = ValidationConstraint(instruction="Must exist.", severity="error")
        with pytest.raises(ValidationError):
            v.instruction = "changed"


class TestSemanticConstraint:
    def test_from_yaml_dict_minimal(self) -> None:
        data = {"intent": "Directs behavior.", "severity": "error"}
        s = SemanticConstraint.model_validate(data)
        assert s.checks == ()
        assert s.anti_patterns == ()

    def test_from_yaml_dict_full(self) -> None:
        data = {
            "intent": "Behavioral boundary.",
            "checks": ["check1", "check2"],
            "anti_patterns": ["bad1"],
            "severity": "warning",
        }
        s = SemanticConstraint.model_validate(data)
        assert s.checks == ("check1", "check2")
        assert s.anti_patterns == ("bad1",)


class TestNotConstraint:
    def test_from_yaml_dict(self) -> None:
        """YAML shape: {$ref: PATH_BLOCKLIST}"""
        data = {"$ref": "PATH_BLOCKLIST"}
        n = NotConstraint.model_validate(data)
        assert n.ref == "PATH_BLOCKLIST"

    def test_by_python_name(self) -> None:
        n = NotConstraint(ref="PATH_BLOCKLIST")
        assert n.ref == "PATH_BLOCKLIST"


class TestRefString:
    def test_from_yaml_dict(self) -> None:
        data = {"$ref": "context_item_resolved"}
        r = RefString.model_validate(data)
        assert r.ref == "context_item_resolved"


class TestArrayItems:
    def test_single_ref(self) -> None:
        """YAML shape: {$ref: context_item}"""
        data = {"$ref": "context_item_resolved"}
        ai = ArrayItems.model_validate(data)
        assert ai.ref == "context_item_resolved"
        assert ai.one_of is None

    def test_union_one_of(self) -> None:
        """YAML shape: {oneOf: [{$ref: entry}, {$ref: include}]}"""
        data = {
            "oneOf": [
                {"$ref": "example_entry"},
                {"$ref": "include_example"},
            ]
        }
        ai = ArrayItems.model_validate(data)
        assert ai.ref is None
        assert ai.one_of is not None
        assert len(ai.one_of) == 2
        assert ai.one_of[0].ref == "example_entry"
        assert ai.one_of[1].ref == "include_example"


# =============================================================================
# RAW TYPES — model_validate from YAML-shaped dicts
# =============================================================================


class TestRawPrimitive:
    def test_simple_string_yaml(self) -> None:
        """agent_name.yaml shape."""
        data = {
            "name": "agent_name",
            "type": "string",
            "requirement": "mandatory",
            "description": "Kebab-case agent identifier.",
            "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
        }
        p = RawPrimitive.model_validate(data)
        assert p.name == "agent_name"
        assert p.pattern == "^[a-z0-9]+(-[a-z0-9]+)*$"
        assert p.enum is None
        assert p.not_constraint is None

    def test_path_with_format_and_validation_yaml(self) -> None:
        """path_exists_absolute.yaml shape."""
        data = {
            "name": "path_exists_absolute",
            "type": "path_allowed_absolute",
            "format": "path_exists_absolute",
            "requirement": "inherit",
            "validation": {
                "instruction": "Must exist on filesystem.",
                "severity": "error",
            },
            "description": "Absolute path that must exist.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.format == "path_exists_absolute"
        assert p.validation is not None
        assert p.validation.severity == "error"

    def test_path_with_not_constraint_yaml(self) -> None:
        """path_allowed_absolute.yaml shape — has not: {$ref: ...}."""
        data = {
            "name": "path_allowed_absolute",
            "type": "string",
            "format": "path_allowed_absolute",
            "requirement": "inherit",
            "pattern": "^/",
            "not": {"$ref": "PATH_BLOCKLIST"},
            "description": "Absolute path.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.not_constraint is not None
        assert p.not_constraint.ref == "PATH_BLOCKLIST"

    def test_enum_yaml(self) -> None:
        """dispatch_mode.yaml shape."""
        data = {
            "name": "dispatch_mode",
            "type": "string",
            "enum": ["batch", "full"],
            "requirement": "mandatory",
            "description": "How dispatcher feeds work.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.enum == ("batch", "full")

    def test_integer_with_minimum_yaml(self) -> None:
        data = {
            "name": "examples_max_number",
            "type": "integer",
            "requirement": "inherit",
            "minimum": 1,
            "description": "Max examples.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.minimum == 1

    def test_boolean_with_default_yaml(self) -> None:
        data = {
            "name": "example_display_headings",
            "type": "boolean",
            "requirement": "inherit",
            "default": False,
            "description": "Toggle heading display.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.default is False

    def test_with_semantic_yaml(self) -> None:
        """guardrails_constraint.yaml shape."""
        data = {
            "name": "guardrails_constraint",
            "type": "string",
            "requirement": "required",
            "semantic": {
                "intent": "Boundary the agent must not cross.",
                "checks": ["check1", "check2"],
                "anti_patterns": ["bad1"],
                "severity": "warning",
            },
            "description": "Behavioral constraint.",
        }
        p = RawPrimitive.model_validate(data)
        assert p.semantic is not None
        assert p.semantic.intent == "Boundary the agent must not cross."
        assert len(p.semantic.checks) == 2

    def test_missing_required_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawPrimitive.model_validate({"name": "bad"})

    def test_frozen(self) -> None:
        p = RawPrimitive.model_validate(
            {"name": "t", "type": "string", "requirement": "mandatory", "description": "t"}
        )
        with pytest.raises(ValidationError):
            p.name = "changed"

    def test_not_constraint_accessible_by_python_name(self) -> None:
        """populate_by_name=True lets tests use not_constraint= kwarg."""
        from draupnir.structures import NotConstraint

        p = RawPrimitive(
            name="test",
            type="string",
            requirement="inherit",
            description="test",
            not_constraint=NotConstraint(ref="PATH_BLOCKLIST"),
        )
        assert p.not_constraint is not None
        assert p.not_constraint.ref == "PATH_BLOCKLIST"


class TestRawComposed:
    def test_thin_yaml(self) -> None:
        """context_path.yaml shape."""
        data = {
            "name": "context_path",
            "type": "path_allowed_any",
            "requirement": "required",
            "description": "Path to context resource.",
        }
        c = RawComposed.model_validate(data)
        assert c.type == "path_allowed_any"
        assert c.composition is None
        assert c.fields is None

    def test_structural_yaml(self) -> None:
        """include_instruction_resolved.yaml shape."""
        data = {
            "name": "include_instruction_resolved",
            "type": "object",
            "requirement": "optional",
            "description": "An @path reference to .md file.",
            "composition": "AllOf",
            "additional_properties": False,
            "fields": {"include": "path_exists_absolute"},
        }
        c = RawComposed.model_validate(data)
        assert c.type == "object"
        assert c.composition == "AllOf"
        assert c.fields == {"include": "path_exists_absolute"}


class TestRawGroup:
    def test_regular_group_yaml(self) -> None:
        """security_paths.yaml shape."""
        data = {
            "name": "security_paths",
            "type": "object",
            "description": "Filesystem path grants.",
            "composition": "OneOf",
            "additional_properties": False,
            "fields": {
                "security_paths_workspace": "security_paths_workspace",
                "security_paths_allowed_read": "security_paths_allowed_read",
            },
        }
        g = RawGroup.model_validate(data)
        assert len(g.fields) == 2
        assert g.arrays == {}
        assert g.required_fields == ()

    def test_supergroup_with_arrays_yaml(self) -> None:
        """context_resolved.yaml shape."""
        data = {
            "name": "context_resolved",
            "type": "object",
            "description": "Resources the agent needs.",
            "composition": "OneOf",
            "additional_properties": False,
            "arrays": {
                "context_required": "context_required_resolved",
                "context_available": "context_available_resolved",
            },
        }
        g = RawGroup.model_validate(data)
        assert len(g.arrays) == 2
        assert g.fields == {}

    def test_supergroup_mixed_yaml(self) -> None:
        """example_group.yaml shape."""
        data = {
            "name": "example_group",
            "type": "object",
            "description": "Named group of examples.",
            "composition": "Mixed",
            "required_fields": ["example_group_name", "example_entries"],
            "additional_properties": False,
            "fields": {
                "example_group_name": "example_group_name",
                "example_display_headings": "example_display_headings",
                "examples_max_number": "examples_max_number",
            },
            "arrays": {"example_entries": "example_entries"},
        }
        g = RawGroup.model_validate(data)
        assert len(g.fields) == 3
        assert len(g.arrays) == 1
        assert g.required_fields == ("example_group_name", "example_entries")


class TestRawArray:
    def test_single_ref_yaml(self) -> None:
        """context_required_resolved.yaml shape."""
        data = {
            "name": "context_required_resolved",
            "type": "array",
            "items": {"$ref": "context_item_resolved"},
            "description": "Required context resources.",
        }
        a = RawArray.model_validate(data)
        assert a.items.ref == "context_item_resolved"
        assert a.items.one_of is None

    def test_union_refs_yaml(self) -> None:
        """example_entries.yaml shape."""
        data = {
            "name": "example_entries",
            "type": "array",
            "items": {
                "oneOf": [
                    {"$ref": "example_entry"},
                    {"$ref": "include_example"},
                ]
            },
            "description": "Example entries.",
        }
        a = RawArray.model_validate(data)
        assert a.items.ref is None
        assert a.items.one_of is not None
        assert len(a.items.one_of) == 2

    def test_items_required(self) -> None:
        with pytest.raises(ValidationError):
            RawArray.model_validate({"name": "bad", "type": "array"})


class TestRawSection:
    def test_from_yaml(self) -> None:
        """security.yaml shape — sub_components with file paths."""
        data = {
            "name": "security",
            "type": "object",
            "description": "Access control.",
            "composition": "Mixed",
            "required_fields": ["security_capabilities", "security_paths"],
            "additional_properties": False,
            "sub_components": {
                "security_paths": "groups/security_paths.yaml",
                "context": "supergroups/context.yaml",
            },
        }
        s = RawSection.model_validate(data)
        assert len(s.sub_components) == 2
        assert s.required_fields == ("security_capabilities", "security_paths")

    def test_defaults(self) -> None:
        s = RawSection.model_validate({"name": "minimal", "type": "object"})
        assert s.sub_components == {}
        assert s.required_fields == ()
        assert s.additional_properties is False


class TestRawSchema:
    def test_from_yaml(self) -> None:
        """agent-definition.yaml target shape (post Phase 5)."""
        data = {
            "name": "agent-definition",
            "version": 3,
            "description": "Schema for agent definitions.",
            "additional_properties": False,
            "sections": {
                "indirect": "sections/indirect.yaml",
                "task": "sections/task.yaml",
                "security": "sections/security.yaml",
            },
            "required_sections": ["indirect", "task", "security"],
            "optional_sections": [],
        }
        s = RawSchema.model_validate(data)
        assert s.version == 3
        assert len(s.sections) == 3
        assert s.optional_sections == ()

    def test_missing_required_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawSchema.model_validate({"name": "bad"})


# =============================================================================
# WALKED TYPES
# =============================================================================


class TestWalkedTypes:
    def _make_raw_array(self) -> RawArray:
        return RawArray.model_validate(
            {"name": "t", "type": "array", "items": {"$ref": "g"}}
        )

    def test_walked_group(self) -> None:
        raw_group = RawGroup(name="test", type="object", fields={"f": "x.yaml"})
        raw_composed = RawComposed(name="f", type="path_allowed_any")
        wg = WalkedGroup(raw=raw_group, composed_fields=(raw_composed,))
        assert wg.raw.name == "test"
        assert len(wg.composed_fields) == 1

    def test_walked_array(self) -> None:
        raw_array = self._make_raw_array()
        raw_group = RawGroup(name="item", type="object")
        wg = WalkedGroup(raw=raw_group)
        wa = WalkedArray(raw=raw_array, items=(wg,))
        assert len(wa.items) == 1

    def test_walked_section(self) -> None:
        raw_section = RawSection(name="test", type="object")
        raw_group = RawGroup(name="comp", type="object")
        wg = WalkedGroup(raw=raw_group)
        ws = WalkedSection(raw=raw_section, components=(wg,))
        assert len(ws.components) == 1

    def test_walked_schema(self) -> None:
        raw_schema = RawSchema(name="test", version=1, description="test schema")
        raw_section = RawSection(name="s", type="object")
        ws = WalkedSection(raw=raw_section)
        walked = WalkedSchema(raw=raw_schema, sections=(ws,))
        assert len(walked.sections) == 1


# =============================================================================
# RESOLVED TYPES
# =============================================================================


class TestResolvedField:
    def test_create(self) -> None:
        f = ResolvedField(
            name="context_path",
            json_type="string",
            format="path_allowed_any",
            requirement="required",
            description="Path to resource.",
        )
        assert f.json_type == "string"
        assert f.format == "path_allowed_any"

    def test_frozen(self) -> None:
        f = ResolvedField(name="test", json_type="string")
        with pytest.raises(ValidationError):
            f.name = "changed"


class TestResolvedGroup:
    def test_with_fields(self) -> None:
        f = ResolvedField(name="path", json_type="string")
        g = ResolvedGroup(
            name="security_paths",
            composition="OneOf",
            fields=(f,),
            required_fields=("path",),
        )
        assert len(g.fields) == 1
        assert g.required_fields == ("path",)

    def test_with_arrays(self) -> None:
        item_group = ResolvedGroup(name="item", fields=())
        arr = ResolvedArray(name="entries", items=(item_group,))
        g = ResolvedGroup(name="parent", arrays=(arr,))
        assert len(g.arrays) == 1

    def test_with_sub_groups(self) -> None:
        nested = ResolvedGroup(name="nested_obj", fields=())
        parent = ResolvedGroup(name="parent", sub_groups=(nested,))
        assert len(parent.sub_groups) == 1


class TestResolvedArray:
    def test_single_item_type(self) -> None:
        item = ResolvedGroup(name="context_item", fields=())
        a = ResolvedArray(name="context_required", items=(item,))
        assert len(a.items) == 1

    def test_union_item_types(self) -> None:
        item1 = ResolvedGroup(name="entry", fields=())
        item2 = ResolvedGroup(name="include", fields=())
        a = ResolvedArray(name="example_entries", items=(item1, item2))
        assert len(a.items) == 2


class TestResolvedSection:
    def test_create(self) -> None:
        g = ResolvedGroup(name="paths", fields=())
        s = ResolvedSection(
            name="security",
            composition="Mixed",
            required_fields=("paths",),
            components=(g,),
        )
        assert len(s.components) == 1


class TestResolvedSchema:
    def test_create(self) -> None:
        s = ResolvedSection(name="security", components=())
        schema = ResolvedSchema(
            name="agent-definition",
            version=3,
            description="Agent definition schema.",
            required_sections=("security",),
            sections=(s,),
        )
        assert schema.version == 3
        assert len(schema.sections) == 1
