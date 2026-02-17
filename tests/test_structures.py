"""Tests for draupnir.structures — frozen Pydantic models."""

import pytest
from pydantic import ValidationError

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSchema,
    RawSection,
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
# CONSTRAINT MODELS
# =============================================================================


class TestValidationConstraint:
    def test_create(self) -> None:
        v = ValidationConstraint(instruction="Must exist.", severity="error")
        assert v.instruction == "Must exist."
        assert v.severity == "error"

    def test_frozen(self) -> None:
        v = ValidationConstraint(instruction="Must exist.", severity="error")
        with pytest.raises(ValidationError):
            v.instruction = "changed"


class TestSemanticConstraint:
    def test_create_minimal(self) -> None:
        s = SemanticConstraint(intent="Directs behavior.", severity="error")
        assert s.checks == ()
        assert s.anti_patterns == ()

    def test_create_full(self) -> None:
        s = SemanticConstraint(
            intent="Directs behavior.",
            checks=("check1", "check2"),
            anti_patterns=("bad1",),
            severity="warning",
        )
        assert len(s.checks) == 2
        assert len(s.anti_patterns) == 1


# =============================================================================
# RAW TYPES
# =============================================================================


class TestRawPrimitive:
    def test_string_type(self) -> None:
        p = RawPrimitive(
            name="agent_name",
            type="string",
            requirement="mandatory",
            description="Kebab-case agent identifier.",
            pattern="^[a-z0-9]+(-[a-z0-9]+)*$",
        )
        assert p.name == "agent_name"
        assert p.type == "string"
        assert p.pattern is not None
        assert p.enum is None

    def test_path_type_with_format(self) -> None:
        p = RawPrimitive(
            name="path_exists_absolute",
            type="path_allowed_absolute",
            requirement="inherit",
            description="Must exist on filesystem.",
            format="path_exists_absolute",
            validation=ValidationConstraint(
                instruction="Must exist.", severity="error"
            ),
        )
        assert p.format == "path_exists_absolute"
        assert p.validation is not None
        assert p.validation.severity == "error"

    def test_enum_type(self) -> None:
        p = RawPrimitive(
            name="dispatch_mode",
            type="string",
            requirement="mandatory",
            description="How dispatcher feeds work.",
            enum=("batch", "full"),
        )
        assert p.enum == ("batch", "full")

    def test_integer_with_minimum(self) -> None:
        p = RawPrimitive(
            name="examples_max_number",
            type="integer",
            requirement="inherit",
            description="Max examples to include.",
            minimum=1,
        )
        assert p.minimum == 1

    def test_boolean_with_default(self) -> None:
        p = RawPrimitive(
            name="example_display_headings",
            type="boolean",
            requirement="inherit",
            description="Toggle heading display.",
            default=False,
        )
        assert p.default is False

    def test_with_not_ref(self) -> None:
        p = RawPrimitive(
            name="path_allowed_absolute",
            type="string",
            requirement="inherit",
            description="Absolute path.",
            pattern="^/",
            not_ref="PATH_BLOCKLIST",
        )
        assert p.not_ref == "PATH_BLOCKLIST"

    def test_with_semantic(self) -> None:
        p = RawPrimitive(
            name="guardrails_constraint",
            type="string",
            requirement="required",
            description="Behavioral constraint.",
            semantic=SemanticConstraint(
                intent="Boundary the agent must not cross.",
                checks=("check1",),
                anti_patterns=("bad1",),
                severity="warning",
            ),
        )
        assert p.semantic is not None
        assert p.semantic.intent == "Boundary the agent must not cross."

    def test_missing_required_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawPrimitive(name="bad")  # type: ignore[call-arg]

    def test_frozen(self) -> None:
        p = RawPrimitive(
            name="test", type="string", requirement="mandatory", description="test"
        )
        with pytest.raises(ValidationError):
            p.name = "changed"


class TestRawComposed:
    def test_thin(self) -> None:
        c = RawComposed(
            name="context_path",
            type="path_allowed_any",
            requirement="required",
            description="Path to context resource.",
        )
        assert c.composition is None
        assert c.fields is None

    def test_structural(self) -> None:
        c = RawComposed(
            name="include_instruction",
            type="object",
            requirement="optional",
            description="@path reference to .md file.",
            composition="AllOf",
            additional_properties=False,
            fields={"include": "path_exists_absolute"},
        )
        assert c.type == "object"
        assert c.composition == "AllOf"
        assert c.fields == {"include": "path_exists_absolute"}


class TestRawGroup:
    def test_regular_group(self) -> None:
        g = RawGroup(
            name="security_paths",
            type="object",
            composition="OneOf",
            fields={
                "workspace": "composed/security_paths_workspace.yaml",
                "allowed_read": "composed/security_paths_allowed_read.yaml",
            },
        )
        assert len(g.fields) == 2
        assert g.arrays == {}
        assert g.required_fields == ()

    def test_supergroup_with_arrays(self) -> None:
        g = RawGroup(
            name="context",
            type="object",
            composition="OneOf",
            arrays={
                "context_required": "arrays/context_required.yaml",
                "context_available": "arrays/context_available.yaml",
            },
        )
        assert len(g.arrays) == 2
        assert g.fields == {}

    def test_supergroup_mixed(self) -> None:
        g = RawGroup(
            name="example_group",
            type="object",
            composition="Mixed",
            required_fields=("example_group_name", "example_entries"),
            fields={
                "example_group_name": "composed/example_group_name.yaml",
                "example_display_headings": "composed/example_display_headings.yaml",
            },
            arrays={"example_entries": "arrays/example_entries.yaml"},
        )
        assert len(g.fields) == 2
        assert len(g.arrays) == 1
        assert len(g.required_fields) == 2


class TestRawArray:
    def test_single_ref(self) -> None:
        a = RawArray(
            name="context_required",
            type="array",
            description="Required context resources.",
            items_refs=("groups/context_item.yaml",),
        )
        assert len(a.items_refs) == 1

    def test_union_refs(self) -> None:
        a = RawArray(
            name="example_entries",
            type="array",
            description="Example entries.",
            items_refs=(
                "groups/example_entry.yaml",
                "composed/include_example.yaml",
            ),
        )
        assert len(a.items_refs) == 2

    def test_items_refs_required(self) -> None:
        with pytest.raises(ValidationError):
            RawArray(name="bad", type="array")  # type: ignore[call-arg]


class TestRawSection:
    def test_create(self) -> None:
        s = RawSection(
            name="security",
            type="object",
            composition="Mixed",
            required_fields=("security_capabilities", "security_paths"),
            sub_components={
                "security_paths": "groups/security_paths.yaml",
                "context": "supergroups/context.yaml",
            },
        )
        assert len(s.sub_components) == 2
        assert s.required_fields == ("security_capabilities", "security_paths")

    def test_defaults(self) -> None:
        s = RawSection(name="minimal", type="object")
        assert s.sub_components == {}
        assert s.required_fields == ()
        assert s.additional_properties is False


class TestRawSchema:
    def test_create(self) -> None:
        s = RawSchema(
            name="agent-definition",
            version=3,
            description="Schema for agent definitions.",
            sections={
                "indirect": "sections/indirect.yaml",
                "task": "sections/task.yaml",
                "security": "sections/security.yaml",
            },
            required_sections=("indirect", "task", "security"),
        )
        assert s.version == 3
        assert len(s.sections) == 3
        assert s.optional_sections == ()

    def test_missing_required_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawSchema(name="bad")  # type: ignore[call-arg]


# =============================================================================
# WALKED TYPES
# =============================================================================


class TestWalkedTypes:
    def test_walked_group(self) -> None:
        raw_group = RawGroup(name="test", type="object", fields={"f": "x.yaml"})
        raw_composed = RawComposed(name="f", type="path_allowed_any")
        wg = WalkedGroup(raw=raw_group, composed_fields=(raw_composed,))
        assert wg.raw.name == "test"
        assert len(wg.composed_fields) == 1

    def test_walked_array(self) -> None:
        raw_array = RawArray(name="test", type="array", items_refs=("g.yaml",))
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
        raw_schema = RawSchema(
            name="test", version=1, description="test schema"
        )
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
