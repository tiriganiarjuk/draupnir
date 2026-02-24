"""Tests for draupnir.functions.pure.builders — typed JSON Schema output."""

from draupnir.structures import (
    ConditionalRequirement,
    ForbiddenEntry,
    ResolvedArray,
    ResolvedField,
    ResolvedGroup,
    ResolvedSchema,
    ResolvedSection,
    RequirementCondition,
    SchemaConst,
    SchemaEnumConstraint,
    SchemaRef,
    SemanticConstraint,
    ValidationConstraint,
)
from draupnir.functions.pure.builders import (
    build_array,
    build_array_items,
    build_condition_if_clause,
    build_defs,
    build_field,
    build_group,
    build_group_object,
    build_nested_forbidden,
    build_nested_property,
    build_nested_required,
    build_not_block,
    build_only_when_conditional,
    build_root_conditional,
    build_root_if_clause,
    build_schema_document,
    build_section,
    build_semantic_ext,
    classify_array_requirement,
    classify_field_requirement,
    collect_deferred_conditionals,
    collect_shared_groups,
    is_cross_group_conditional,
    is_field_required,
    scan_group_for_deferred,
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

    def test_not_block_extension(self) -> None:
        entries = (ForbiddenEntry(name="path_forbidden_root", const="/"),)
        field = ResolvedField(
            name="path", json_type="string",
            not_entries=entries,
        )
        result = build_field(field)
        assert result.x_not is not None
        assert result.x_not.forbidden[0].name == "path_forbidden_root"
        assert result.x_not.forbidden[0].const == "/"

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


class TestBuildNotBlock:
    def test_none_input(self) -> None:
        assert build_not_block(None) is None

    def test_with_entries(self) -> None:
        entries = (ForbiddenEntry(name="path_forbidden_root", const="/"),)
        result = build_not_block(entries)
        assert result is not None
        assert len(result.forbidden) == 1
        assert result.forbidden[0].name == "path_forbidden_root"


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


class TestIsCrossGroupConditional:
    def test_dot_path_is_cross_group(self) -> None:
        """field: task.return.return_mode → cross-group."""
        cond = ConditionalRequirement(
            field="task.return.return_mode",
            in_values=("metrics-output", "output"),
        )
        assert is_cross_group_conditional(cond) is True

    def test_simple_field_is_local(self) -> None:
        """field: dispatch_mode → local."""
        cond = ConditionalRequirement(field="dispatch_mode", equals="batch")
        assert is_cross_group_conditional(cond) is False


class TestCrossGroupConditionalSkipped:
    def test_cross_group_not_emitted(self) -> None:
        """Cross-group conditional → not in required, no local conditional."""
        req = RequirementCondition(
            only_when=ConditionalRequirement(
                field="task.return.return_mode",
                in_values=("metrics-output", "output"),
            ),
        )
        f = ResolvedField(
            name="output_kind", json_type="string", requirement=req,
        )
        name, cond = classify_field_requirement(f)
        assert name is None
        assert cond is None  # skipped, not emitted

    def test_local_conditional_still_works(self) -> None:
        """Non-dot-path conditional → still emits normally."""
        req = RequirementCondition(
            only_when=ConditionalRequirement(
                field="dispatch_mode", equals="batch",
            ),
        )
        f = ResolvedField(
            name="batch_size", json_type="integer", requirement=req,
        )
        name, cond = classify_field_requirement(f)
        assert name is None
        assert cond is not None
        assert cond.then_.required == ("batch_size",)


class TestBuildConditionIfClause:
    def test_equals(self) -> None:
        cond = ConditionalRequirement(field="mode", equals="batch")
        result = build_condition_if_clause(cond)
        assert result.properties is not None
        assert isinstance(result.properties.root["mode"], SchemaConst)
        assert result.properties.root["mode"].const == "batch"

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
        assert isinstance(result.properties.root["mode"], SchemaEnumConstraint)
        assert result.properties.root["mode"].enum == ("batch", "stream")


class TestBuildOnlyWhenConditional:
    def test_produces_if_then_else(self) -> None:
        cond = ConditionalRequirement(field="mode", equals="batch")
        result = build_only_when_conditional(cond, "batch_size")
        assert result.if_.properties is not None
        assert result.then_.required == ("batch_size",)
        assert result.else_ is not None
        assert result.else_.properties is not None
        assert result.else_.properties.root["batch_size"] is False


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


class TestBuildArrayWithConstraints:
    def test_constraints_passed_through(self) -> None:
        """min_items/max_items/unique_items appear in output."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(
            name="constraints",
            items=item,
            min_items=1,
            max_items=10,
            unique_items=True,
        )
        result = build_array(arr)
        assert result.min_items == 1
        assert result.max_items == 10
        assert result.unique_items is True

    def test_constraints_serialization(self) -> None:
        """model_dump produces minItems, maxItems, uniqueItems."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(
            name="constraints",
            items=item,
            min_items=2,
            max_items=5,
            unique_items=True,
        )
        result = build_array(arr)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped["minItems"] == 2
        assert dumped["maxItems"] == 5
        assert dumped["uniqueItems"] is True

    def test_semantic_passed_through(self) -> None:
        """x-semantic appears in array output."""
        sc = SemanticConstraint(
            intent="Boundary enforcement.",
            severity="error",
            checks=("check1",),
        )
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(
            name="constraints", items=item, semantic=sc,
        )
        result = build_array(arr)
        assert result.x_semantic is not None
        assert result.x_semantic.intent == "Boundary enforcement."


class TestBuildArrayItemsField:
    def test_resolved_field_items(self) -> None:
        """ResolvedField items → SchemaField."""
        item = ResolvedField(name="_items", json_type="integer")
        result = build_array_items(item)
        assert result.type == "integer"


class TestClassifyArrayRequirement:
    def test_in_required_fields(self) -> None:
        """Array name in parent's required_fields → required."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(name="entries", items=item)
        name, cond = classify_array_requirement(arr, ("entries",))
        assert name == "entries"
        assert cond is None

    def test_own_requirement_mandatory(self) -> None:
        """Composed array with requirement='mandatory' → required."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(
            name="constraints", items=item, requirement="mandatory",
        )
        name, cond = classify_array_requirement(arr, ())
        assert name == "constraints"
        assert cond is None

    def test_own_requirement_optional(self) -> None:
        """Composed array with requirement='optional' → neither."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(
            name="constraints", items=item, requirement="optional",
        )
        name, cond = classify_array_requirement(arr, ())
        assert name is None
        assert cond is None

    def test_own_requirement_conditional(self) -> None:
        """Composed array with conditional requirement → allOf."""
        cond_req = RequirementCondition(
            only_when=ConditionalRequirement(
                field="mode", equals="batch",
            ),
        )
        item = ResolvedField(name="_items", json_type="integer")
        arr = ResolvedArray(
            name="batch_sizes", items=item, requirement=cond_req,
        )
        name, cond = classify_array_requirement(arr, ())
        assert name is None
        assert cond is not None
        assert cond.then_.required == ("batch_sizes",)

    def test_no_requirement(self) -> None:
        """Array with no requirement and not in required_fields → neither."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(name="entries", items=item)
        name, cond = classify_array_requirement(arr, ())
        assert name is None
        assert cond is None


class TestBuildGroupWithComposedArrays:
    def test_required_composed_array(self) -> None:
        """Composed array with requirement='mandatory' → in required."""
        item = ResolvedField(name="_items", json_type="string")
        arr = ResolvedArray(
            name="constraints", items=item, requirement="mandatory",
        )
        group = ResolvedGroup(name="guardrails", arrays=(arr,))
        result = build_group(group)
        assert "constraints" in result.properties
        assert result.properties["constraints"].type == "array"
        assert result.required == ("constraints",)

    def test_conditional_composed_array(self) -> None:
        """Composed array with conditional requirement → allOf."""
        cond_req = RequirementCondition(
            only_when=ConditionalRequirement(
                field="mode", equals="batch",
            ),
        )
        item = ResolvedField(name="_items", json_type="integer")
        arr = ResolvedArray(
            name="batch_sizes", items=item, requirement=cond_req,
        )
        group = ResolvedGroup(name="execution", arrays=(arr,))
        result = build_group(group)
        assert "batch_sizes" in result.properties
        assert result.required is None
        assert result.all_of is not None
        assert len(result.all_of) == 1
        assert result.all_of[0].then_.required == ("batch_sizes",)


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

    def test_with_arrays(self) -> None:
        """Section with arrays → arrays in output properties."""
        item = ResolvedGroup(name="criterion")
        arr = ResolvedArray(name="success_criteria", items=(item,))
        section = ResolvedSection(
            name="criteria",
            arrays=(arr,),
            required_fields=("success_criteria",),
        )
        result = build_section(section)
        assert "success_criteria" in result.properties
        assert result.properties["success_criteria"].type == "array"
        assert result.required == ("success_criteria",)

    def test_with_components_and_arrays(self) -> None:
        """Section with both components and arrays."""
        comp = ResolvedGroup(name="paths")
        item = ResolvedGroup(name="item")
        arr = ResolvedArray(name="entries", items=(item,))
        section = ResolvedSection(
            name="execution",
            components=(comp,),
            arrays=(arr,),
            required_fields=("paths", "entries"),
        )
        result = build_section(section)
        assert "paths" in result.properties
        assert "entries" in result.properties
        assert set(result.required) == {"paths", "entries"}

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
        assert doc.schema_id == "test-schema-v1"
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
        assert dumped["$id"] == "test-schema-v1"
        ws = dumped["properties"]["security"]["properties"]["paths"]["properties"]["workspace"]
        assert ws["type"] == "string"
        assert ws["format"] == "path_exists_absolute"
        assert ws["pattern"] == "^/"


# =============================================================================
# CROSS-SECTION CONDITIONALS
# =============================================================================


class TestNestedPathBuilders:
    def test_nested_property_single_segment(self) -> None:
        leaf = SchemaEnumConstraint(enum=("a", "b"))
        result = build_nested_property(("mode",), leaf)
        dumped = result.model_dump(exclude_none=True)
        assert dumped["properties"]["mode"]["enum"] == ("a", "b")

    def test_nested_property_three_segments(self) -> None:
        leaf = SchemaConst(const="batch")
        result = build_nested_property(("task", "return", "mode"), leaf)
        dumped = result.model_dump(exclude_none=True)
        inner = dumped["properties"]["task"]["properties"]["return"]["properties"]["mode"]
        assert inner == {"const": "batch"}

    def test_nested_required(self) -> None:
        result = build_nested_required(("security", "io"), "output_kind")
        dumped = result.model_dump(exclude_none=True)
        inner = dumped["properties"]["security"]["properties"]["io"]
        assert inner == {"required": ("output_kind",)}

    def test_nested_forbidden(self) -> None:
        result = build_nested_forbidden(("security", "io"), "output_kind")
        dumped = result.model_dump(exclude_none=True)
        inner = dumped["properties"]["security"]["properties"]["io"]
        assert inner == {"properties": {"output_kind": False}}

    def test_nested_required_empty_path(self) -> None:
        result = build_nested_required((), "field_name")
        dumped = result.model_dump(exclude_none=True)
        assert dumped == {"required": ("field_name",)}

    def test_nested_forbidden_empty_path(self) -> None:
        result = build_nested_forbidden((), "field_name")
        dumped = result.model_dump(exclude_none=True)
        assert dumped == {"properties": {"field_name": False}}


class TestRootIfClause:
    def test_in_values(self) -> None:
        cond = ConditionalRequirement(
            field="task.return.return_mode",
            in_values=("metrics-output", "output"),
        )
        result = build_root_if_clause(cond)
        dumped = result.model_dump(exclude_none=True)
        leaf = dumped["properties"]["task"]["properties"]["return"]["properties"]["return_mode"]
        assert leaf["enum"] == ("metrics-output", "output")

    def test_equals(self) -> None:
        cond = ConditionalRequirement(
            field="task.dispatch.mode", equals="batch",
        )
        result = build_root_if_clause(cond)
        dumped = result.model_dump(exclude_none=True)
        leaf = dumped["properties"]["task"]["properties"]["dispatch"]["properties"]["mode"]
        assert leaf == {"const": "batch"}

    def test_present(self) -> None:
        cond = ConditionalRequirement(
            field="task.return.return_mode", present=True,
        )
        result = build_root_if_clause(cond)
        dumped = result.model_dump(exclude_none=True)
        inner = dumped["properties"]["task"]["properties"]["return"]
        assert inner == {"required": ("return_mode",)}


class TestBuildRootConditional:
    def test_full_root_conditional(self) -> None:
        cond = ConditionalRequirement(
            field="task.return.return_mode",
            in_values=("metrics-output", "output"),
        )
        result = build_root_conditional(
            cond, "security_io_output_kind", ("security", "security_io"),
        )
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        # if clause: nested to task.return.return_mode
        if_leaf = dumped["if"]["properties"]["task"]["properties"]["return"]["properties"]["return_mode"]
        assert if_leaf["enum"] == ("metrics-output", "output")
        # then clause: security.security_io requires field
        then_inner = dumped["then"]["properties"]["security"]["properties"]["security_io"]
        assert then_inner == {"required": ("security_io_output_kind",)}
        # else clause: security.security_io.field = false
        else_inner = dumped["else"]["properties"]["security"]["properties"]["security_io"]
        assert else_inner == {"properties": {"security_io_output_kind": False}}


class TestCollectDeferredConditionals:
    def _make_schema_with_cross_group(self) -> ResolvedSchema:
        """Build a schema with one cross-section conditional field."""
        cross_field = ResolvedField(
            name="output_kind",
            json_type="string",
            requirement=RequirementCondition(
                only_when=ConditionalRequirement(
                    field="task.return.return_mode",
                    in_values=("metrics-output", "output"),
                ),
            ),
        )
        io_group = ResolvedGroup(
            name="security_io",
            fields=(cross_field,),
        )
        section = ResolvedSection(
            name="security",
            components=(io_group,),
        )
        return ResolvedSchema(
            name="test",
            version=1,
            description="Test.",
            sections=(section,),
        )

    def test_deferred_collected(self) -> None:
        schema = self._make_schema_with_cross_group()
        result = collect_deferred_conditionals(schema)
        assert len(result) == 1
        dumped = result[0].model_dump(by_alias=True, exclude_none=True)
        assert "if" in dumped
        assert "then" in dumped
        assert "else" in dumped

    def test_deferred_in_schema_document(self) -> None:
        schema = self._make_schema_with_cross_group()
        doc = build_schema_document(schema)
        dumped = doc.model_dump(by_alias=True, exclude_none=True)
        assert "allOf" in dumped
        assert len(dumped["allOf"]) == 1
        cond = dumped["allOf"][0]
        then_inner = cond["then"]["properties"]["security"]["properties"]["security_io"]
        assert then_inner == {"required": ("output_kind",)}

    def test_no_deferred_no_allof(self) -> None:
        """Schema with no cross-group conditionals → no allOf."""
        field = ResolvedField(name="path", json_type="string")
        group = ResolvedGroup(name="paths", fields=(field,))
        section = ResolvedSection(name="security", components=(group,))
        schema = ResolvedSchema(
            name="test", version=1, description="Test.",
            sections=(section,),
        )
        doc = build_schema_document(schema)
        dumped = doc.model_dump(by_alias=True, exclude_none=True)
        assert "allOf" not in dumped

    def test_scan_skips_local_conditionals(self) -> None:
        """Local conditionals are NOT deferred."""
        local_field = ResolvedField(
            name="batch_size",
            json_type="integer",
            requirement=RequirementCondition(
                only_when=ConditionalRequirement(
                    field="dispatch_mode", equals="batch",
                ),
            ),
        )
        group = ResolvedGroup(name="dispatch", fields=(local_field,))
        result = scan_group_for_deferred(group, ("task", "dispatch"))
        assert len(result) == 0

    def test_scan_finds_nested_subgroup(self) -> None:
        """Cross-group conditional in a sub-group is found."""
        cross_field = ResolvedField(
            name="output_kind",
            json_type="string",
            requirement=RequirementCondition(
                only_when=ConditionalRequirement(
                    field="task.return.mode",
                    in_values=("output",),
                ),
            ),
        )
        inner = ResolvedGroup(name="io", fields=(cross_field,))
        outer = ResolvedGroup(
            name="security_top", fields=(), sub_groups=(inner,),
        )
        result = scan_group_for_deferred(outer, ("security", "security_top"))
        assert len(result) == 1
        dumped = result[0].model_dump(by_alias=True, exclude_none=True)
        then_path = dumped["then"]["properties"]["security"]["properties"]["security_top"]["properties"]["io"]
        assert then_path == {"required": ("output_kind",)}


# =============================================================================
# $DEFS / $REF DEDUPLICATION
# =============================================================================


def _make_shared_schema() -> ResolvedSchema:
    """Build a schema with the same group referenced by two arrays.

    Simulates the render_parameter_item case: both input.parameters
    and dispatcher.parameters reference the same group file.
    """
    shared_group = ResolvedGroup(
        name="parameter_item",
        source_ref="groups/render_parameter_item.yaml",
        fields=(
            ResolvedField(name="name", json_type="string", requirement="mandatory"),
            ResolvedField(name="value", json_type="string"),
        ),
    )
    shared_group_dup = ResolvedGroup(
        name="parameter_item",
        source_ref="groups/render_parameter_item.yaml",
        fields=(
            ResolvedField(name="name", json_type="string", requirement="mandatory"),
            ResolvedField(name="value", json_type="string"),
        ),
    )
    arr_input = ResolvedArray(
        name="parameters", items=(shared_group,),
    )
    arr_dispatch = ResolvedArray(
        name="parameters", items=(shared_group_dup,),
    )
    input_group = ResolvedGroup(
        name="input", arrays=(arr_input,),
    )
    dispatch_group = ResolvedGroup(
        name="dispatcher", arrays=(arr_dispatch,),
    )
    section_input = ResolvedSection(
        name="input", components=(input_group,),
    )
    section_dispatch = ResolvedSection(
        name="dispatcher", components=(dispatch_group,),
    )
    return ResolvedSchema(
        name="universal-render",
        version=1,
        description="Test schema with shared groups.",
        sections=(section_input, section_dispatch),
        required_sections=("input", "dispatcher"),
    )


class TestCollectSharedGroups:
    def test_finds_duplicates(self) -> None:
        """Two arrays referencing same source_ref → detected as shared."""
        schema = _make_shared_schema()
        shared = collect_shared_groups(schema)
        assert "groups/render_parameter_item.yaml" in shared
        assert shared["groups/render_parameter_item.yaml"].name == "parameter_item"

    def test_ignores_unique(self) -> None:
        """Groups with different source_refs → not shared."""
        group_a = ResolvedGroup(
            name="a", source_ref="groups/a.yaml",
        )
        group_b = ResolvedGroup(
            name="b", source_ref="groups/b.yaml",
        )
        arr_a = ResolvedArray(name="items_a", items=(group_a,))
        arr_b = ResolvedArray(name="items_b", items=(group_b,))
        section = ResolvedSection(
            name="sec", arrays=(arr_a, arr_b),
        )
        schema = ResolvedSchema(
            name="test", version=1, description="Test.",
            sections=(section,),
        )
        shared = collect_shared_groups(schema)
        assert len(shared) == 0

    def test_ignores_none_source_ref(self) -> None:
        """Synthetic groups (source_ref=None) → never counted."""
        synthetic = ResolvedGroup(name="synth", source_ref=None)
        arr = ResolvedArray(name="items", items=(synthetic,))
        section = ResolvedSection(name="sec", arrays=(arr, arr))
        schema = ResolvedSchema(
            name="test", version=1, description="Test.",
            sections=(section,),
        )
        shared = collect_shared_groups(schema)
        assert len(shared) == 0


class TestBuildGroupWithSharedRefs:
    def test_emits_ref_for_shared(self) -> None:
        """Group with source_ref in shared_refs → SchemaRef."""
        group = ResolvedGroup(
            name="parameter_item",
            source_ref="groups/render_parameter_item.yaml",
        )
        shared_refs = frozenset({"groups/render_parameter_item.yaml"})
        result = build_group(group, shared_refs)
        assert isinstance(result, SchemaRef)
        assert result.ref == "#/$defs/parameter_item"

    def test_inlines_when_not_shared(self) -> None:
        """Group without source_ref in shared_refs → SchemaObject."""
        group = ResolvedGroup(
            name="unique_group",
            source_ref="groups/unique.yaml",
        )
        shared_refs = frozenset({"groups/other.yaml"})
        result = build_group(group, shared_refs)
        assert not isinstance(result, SchemaRef)
        assert result.type == "object"

    def test_inlines_when_no_shared_refs(self) -> None:
        """No shared_refs parameter → normal inline build."""
        group = ResolvedGroup(name="test_group")
        result = build_group(group)
        assert not isinstance(result, SchemaRef)
        assert result.type == "object"


class TestBuildGroupObject:
    def test_builds_full_content(self) -> None:
        """build_group_object always builds inline, never $ref."""
        group = ResolvedGroup(
            name="parameter_item",
            source_ref="groups/render_parameter_item.yaml",
            fields=(
                ResolvedField(name="name", json_type="string"),
            ),
        )
        shared_refs = frozenset({"groups/render_parameter_item.yaml"})
        result = build_group_object(group, shared_refs)
        assert result.type == "object"
        assert "name" in result.properties


class TestBuildDefs:
    def test_builds_defs_from_shared(self) -> None:
        """Shared groups → $defs dict keyed by group name."""
        group = ResolvedGroup(
            name="parameter_item",
            source_ref="groups/render_parameter_item.yaml",
            fields=(
                ResolvedField(name="name", json_type="string"),
            ),
        )
        shared = {"groups/render_parameter_item.yaml": group}
        shared_refs = frozenset(shared.keys())
        defs = build_defs(shared, shared_refs)
        assert "parameter_item" in defs
        assert defs["parameter_item"].type == "object"
        assert "name" in defs["parameter_item"].properties


class TestSchemaDocumentWithDefs:
    def test_shared_groups_produce_defs(self) -> None:
        """Full schema with shared groups → $defs and $ref in output."""
        schema = _make_shared_schema()
        doc = build_schema_document(schema)
        dumped = doc.model_dump(by_alias=True, exclude_none=True)
        assert "$defs" in dumped
        assert "parameter_item" in dumped["$defs"]
        # Both arrays should reference via $ref
        input_params = dumped["properties"]["input"]["properties"]["input"]["properties"]["parameters"]
        assert input_params["items"] == {"$ref": "#/$defs/parameter_item"}
        dispatch_params = dumped["properties"]["dispatcher"]["properties"]["dispatcher"]["properties"]["parameters"]
        assert dispatch_params["items"] == {"$ref": "#/$defs/parameter_item"}

    def test_no_shared_no_defs(self) -> None:
        """Schema without shared groups → no $defs in output."""
        schema = ResolvedSchema(
            name="test", version=1, description="Test.",
        )
        doc = build_schema_document(schema)
        dumped = doc.model_dump(by_alias=True, exclude_none=True)
        assert "$defs" not in dumped

    def test_defs_content_matches_inline(self) -> None:
        """$defs entry content matches what inline would have been."""
        schema = _make_shared_schema()
        shared = collect_shared_groups(schema)
        shared_refs = frozenset(shared.keys())
        defs = build_defs(shared, shared_refs)
        # Build the same group without $ref to compare
        group = shared["groups/render_parameter_item.yaml"]
        inline = build_group_object(group, None)
        defs_entry = defs["parameter_item"]
        assert defs_entry.description == inline.description
        assert set(defs_entry.properties.keys()) == set(inline.properties.keys())
