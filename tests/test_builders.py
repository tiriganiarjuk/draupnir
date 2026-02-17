"""Tests for draupnir.functions.pure.builders — typed JSON Schema output."""

from draupnir.structures import (
    ConditionalRequirement,
    ResolvedArray,
    ResolvedField,
    ResolvedGroup,
    ResolvedSchema,
    ResolvedSection,
    RequirementCondition,
    SchemaConst,
    SchemaEnumConstraint,
    SemanticConstraint,
    ValidationConstraint,
)
from draupnir.functions.pure.builders import (
    build_array,
    build_array_items,
    build_condition_if_clause,
    build_field,
    build_group,
    build_not_ref,
    build_only_when_conditional,
    build_schema_document,
    build_section,
    build_semantic_ext,
    classify_field_requirement,
    is_field_required,
)


# =============================================================================
# FIELD BUILDING
# =============================================================================


class TestBuildField:
    def test_minimal_field(self) -> None:
        field = ResolvedField(name="name", json_type="string")
        result = build_field(field)
        assert result.type == "string"
        assert result.description is None
        assert result.format is None

    def test_full_field(self) -> None:
        field = ResolvedField(
            name="workspace",
            json_type="string",
            description="Workspace path.",
            format="path_exists_absolute",
            pattern="^/",
        )
        result = build_field(field)
        assert result.type == "string"
        assert result.description == "Workspace path."
        assert result.format == "path_exists_absolute"
        assert result.pattern == "^/"

    def test_enum_field(self) -> None:
        field = ResolvedField(
            name="mode",
            json_type="string",
            enum_values=("batch", "full"),
        )
        result = build_field(field)
        assert result.enum == ("batch", "full")

    def test_default_and_minimum(self) -> None:
        field = ResolvedField(
            name="count",
            json_type="integer",
            default=10,
            minimum=1,
        )
        result = build_field(field)
        assert result.default == 10
        assert result.minimum == 1

    def test_validation_extension(self) -> None:
        vc = ValidationConstraint(
            instruction="Must exist on filesystem.",
            severity="error",
        )
        field = ResolvedField(
            name="path", json_type="string", validation=vc,
        )
        result = build_field(field)
        assert result.x_validation is not None
        assert result.x_validation.instruction == "Must exist on filesystem."

    def test_not_ref_extension(self) -> None:
        field = ResolvedField(
            name="path", json_type="string",
            not_ref="PATH_BLOCKLIST",
        )
        result = build_field(field)
        assert result.x_not is not None
        assert result.x_not.ref == "PATH_BLOCKLIST"

    def test_semantic_extension(self) -> None:
        sc = SemanticConstraint(
            intent="Directs behavior.",
            checks=("check1",),
            severity="error",
        )
        field = ResolvedField(
            name="instruction", json_type="string", semantic=sc,
        )
        result = build_field(field)
        assert result.x_semantic is not None
        assert result.x_semantic.intent == "Directs behavior."
        assert result.x_semantic.checks == ("check1",)
        assert result.x_semantic.anti_patterns is None


# =============================================================================
# EXTENSION HELPERS
# =============================================================================


class TestBuildNotRef:
    def test_none_input(self) -> None:
        assert build_not_ref(None) is None

    def test_string_input(self) -> None:
        result = build_not_ref("PATH_BLOCKLIST")
        assert result is not None
        assert result.ref == "PATH_BLOCKLIST"


class TestBuildSemanticExt:
    def test_none_input(self) -> None:
        assert build_semantic_ext(None) is None

    def test_with_checks(self) -> None:
        sc = SemanticConstraint(
            intent="Quality.",
            checks=("a", "b"),
            anti_patterns=("x",),
            severity="warning",
        )
        result = build_semantic_ext(sc)
        assert result is not None
        assert result.checks == ("a", "b")
        assert result.anti_patterns == ("x",)

    def test_empty_checks_become_none(self) -> None:
        sc = SemanticConstraint(intent="Test.", severity="info")
        result = build_semantic_ext(sc)
        assert result is not None
        assert result.checks is None
        assert result.anti_patterns is None


# =============================================================================
# REQUIREMENT CLASSIFICATION
# =============================================================================


class TestIsFieldRequired:
    def test_mandatory(self) -> None:
        f = ResolvedField(name="x", json_type="string", requirement="mandatory")
        assert is_field_required(f) is True

    def test_required(self) -> None:
        f = ResolvedField(name="x", json_type="string", requirement="required")
        assert is_field_required(f) is True

    def test_optional(self) -> None:
        f = ResolvedField(name="x", json_type="string", requirement="optional")
        assert is_field_required(f) is False

    def test_conditional(self) -> None:
        cond = RequirementCondition(
            only_when=ConditionalRequirement(field="mode", equals="batch"),
        )
        f = ResolvedField(name="x", json_type="string", requirement=cond)
        assert is_field_required(f) is False

    def test_none(self) -> None:
        f = ResolvedField(name="x", json_type="string")
        assert is_field_required(f) is False


class TestClassifyFieldRequirement:
    def test_required_returns_name(self) -> None:
        f = ResolvedField(name="x", json_type="string", requirement="mandatory")
        name, cond = classify_field_requirement(f)
        assert name == "x"
        assert cond is None

    def test_conditional_returns_conditional(self) -> None:
        req = RequirementCondition(
            only_when=ConditionalRequirement(field="mode", equals="batch"),
        )
        f = ResolvedField(name="x", json_type="string", requirement=req)
        name, cond = classify_field_requirement(f)
        assert name is None
        assert cond is not None
        assert cond.then_.required == ("x",)

    def test_optional_returns_neither(self) -> None:
        f = ResolvedField(name="x", json_type="string", requirement="optional")
        name, cond = classify_field_requirement(f)
        assert name is None
        assert cond is None


class TestBuildConditionIfClause:
    def test_equals(self) -> None:
        cond = ConditionalRequirement(field="mode", equals="batch")
        result = build_condition_if_clause(cond)
        assert result.properties is not None
        assert isinstance(result.properties["mode"], SchemaConst)
        assert result.properties["mode"].const == "batch"

    def test_present(self) -> None:
        cond = ConditionalRequirement(field="mode", present=True)
        result = build_condition_if_clause(cond)
        assert result.required == ("mode",)

    def test_in_values(self) -> None:
        cond = ConditionalRequirement.model_validate(
            {"field": "mode", "in": ["batch", "stream"]},
        )
        result = build_condition_if_clause(cond)
        assert result.properties is not None
        assert isinstance(result.properties["mode"], SchemaEnumConstraint)
        assert result.properties["mode"].enum == ("batch", "stream")


class TestBuildOnlyWhenConditional:
    def test_produces_if_then_else(self) -> None:
        cond = ConditionalRequirement(field="mode", equals="batch")
        result = build_only_when_conditional(cond, "batch_size")
        assert result.if_.properties is not None
        assert result.then_.required == ("batch_size",)
        assert result.else_ is not None
        assert result.else_.properties is not None
        assert result.else_.properties["batch_size"] is False


# =============================================================================
# GROUP BUILDING
# =============================================================================


class TestBuildGroup:
    def test_empty_group(self) -> None:
        group = ResolvedGroup(name="empty")
        result = build_group(group)
        assert result.type == "object"
        assert result.properties == {}
        assert result.required is None
        assert result.additional_properties is False

    def test_with_fields(self) -> None:
        group = ResolvedGroup(
            name="paths",
            fields=(
                ResolvedField(
                    name="workspace", json_type="string",
                    requirement="mandatory",
                ),
                ResolvedField(
                    name="output", json_type="string",
                    requirement="optional",
                ),
            ),
        )
        result = build_group(group)
        assert "workspace" in result.properties
        assert "output" in result.properties
        assert result.required == ("workspace",)

    def test_oneof_composition(self) -> None:
        group = ResolvedGroup(name="g", composition="OneOf")
        result = build_group(group)
        assert result.min_properties == 1

    def test_additional_properties_true(self) -> None:
        group = ResolvedGroup(name="g", additional_properties=True)
        result = build_group(group)
        assert result.additional_properties is None

    def test_with_sub_groups(self) -> None:
        child = ResolvedGroup(
            name="nested",
            fields=(
                ResolvedField(
                    name="value", json_type="string",
                    requirement="mandatory",
                ),
            ),
        )
        parent = ResolvedGroup(
            name="parent",
            sub_groups=(child,),
            required_fields=("nested",),
        )
        result = build_group(parent)
        assert "nested" in result.properties
        nested = result.properties["nested"]
        assert nested.type == "object"
        assert "nested" in result.required

    def test_with_arrays(self) -> None:
        item_group = ResolvedGroup(name="item")
        arr = ResolvedArray(name="entries", items=(item_group,))
        group = ResolvedGroup(
            name="parent",
            arrays=(arr,),
            required_fields=("entries",),
        )
        result = build_group(group)
        assert "entries" in result.properties
        entries = result.properties["entries"]
        assert entries.type == "array"
        assert "entries" in result.required

    def test_conditional_requirement(self) -> None:
        cond = RequirementCondition(
            only_when=ConditionalRequirement(field="mode", equals="batch"),
        )
        group = ResolvedGroup(
            name="g",
            fields=(
                ResolvedField(
                    name="batch_size", json_type="integer",
                    requirement=cond,
                ),
            ),
        )
        result = build_group(group)
        assert result.required is None
        assert result.all_of is not None
        assert len(result.all_of) == 1
        assert result.all_of[0].then_.required == ("batch_size",)


# =============================================================================
# ARRAY BUILDING
# =============================================================================


class TestBuildArray:
    def test_single_item_type(self) -> None:
        item = ResolvedGroup(name="entry")
        arr = ResolvedArray(name="entries", items=(item,))
        result = build_array(arr)
        assert result.type == "array"
        assert result.items.type == "object"

    def test_with_description(self) -> None:
        item = ResolvedGroup(name="entry")
        arr = ResolvedArray(
            name="entries", items=(item,),
            description="List of entries.",
        )
        result = build_array(arr)
        assert result.description == "List of entries."


class TestBuildArrayItems:
    def test_single_item(self) -> None:
        item = ResolvedGroup(name="entry")
        result = build_array_items((item,))
        assert result.type == "object"

    def test_multiple_items_oneof(self) -> None:
        item1 = ResolvedGroup(name="entry")
        item2 = ResolvedGroup(name="include")
        result = build_array_items((item1, item2))
        assert hasattr(result, "one_of")
        assert len(result.one_of) == 2


# =============================================================================
# SECTION BUILDING
# =============================================================================


class TestBuildSection:
    def test_empty_section(self) -> None:
        section = ResolvedSection(name="security")
        result = build_section(section)
        assert result.type == "object"
        assert result.properties == {}
        assert result.additional_properties is False

    def test_with_components(self) -> None:
        comp = ResolvedGroup(
            name="paths",
            fields=(
                ResolvedField(
                    name="workspace", json_type="string",
                    requirement="mandatory",
                ),
            ),
        )
        section = ResolvedSection(
            name="security",
            components=(comp,),
            required_fields=("paths",),
        )
        result = build_section(section)
        assert "paths" in result.properties
        assert result.required == ("paths",)

    def test_oneof_section(self) -> None:
        section = ResolvedSection(name="s", composition="OneOf")
        result = build_section(section)
        assert result.min_properties == 1


# =============================================================================
# FULL SCHEMA DOCUMENT BUILDING
# =============================================================================


class TestBuildSchemaDocument:
    def test_minimal_schema(self) -> None:
        schema = ResolvedSchema(
            name="test",
            version=1,
            description="Test schema.",
        )
        doc = build_schema_document(schema)
        assert doc.schema_uri == "https://json-schema.org/draft/2020-12/schema"
        assert doc.schema_id == "agent-test"
        assert doc.title == "test"
        assert doc.description == "Test schema."
        assert doc.type == "object"
        assert doc.properties == {}
        assert doc.additional_properties is False

    def test_with_sections(self) -> None:
        comp = ResolvedGroup(name="paths")
        section = ResolvedSection(
            name="security",
            components=(comp,),
            required_fields=("paths",),
        )
        schema = ResolvedSchema(
            name="agent-definition",
            version=3,
            description="Agent definition.",
            sections=(section,),
            required_sections=("security",),
        )
        doc = build_schema_document(schema)
        assert "security" in doc.properties
        assert doc.required == ("security",)
        sec = doc.properties["security"]
        assert "paths" in sec.properties
        assert sec.required == ("paths",)

    def test_serialization_round_trip(self) -> None:
        """Verify model_dump produces valid JSON Schema structure."""
        field = ResolvedField(
            name="workspace",
            json_type="string",
            requirement="mandatory",
            format="path_exists_absolute",
            pattern="^/",
            description="Workspace path.",
        )
        group = ResolvedGroup(name="paths", fields=(field,))
        section = ResolvedSection(
            name="security",
            components=(group,),
            required_fields=("paths",),
        )
        schema = ResolvedSchema(
            name="test",
            version=1,
            description="Full test.",
            sections=(section,),
            required_sections=("security",),
        )
        doc = build_schema_document(schema)
        dumped = doc.model_dump(by_alias=True, exclude_none=True)
        assert dumped["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert dumped["$id"] == "agent-test"
        ws = dumped["properties"]["security"]["properties"]["paths"]["properties"]["workspace"]
        assert ws["type"] == "string"
        assert ws["format"] == "path_exists_absolute"
        assert ws["pattern"] == "^/"
