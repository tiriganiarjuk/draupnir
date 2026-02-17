"""Tests for draupnir.functions.pure.resolvers — type adoption chains."""

import pytest

from draupnir.structures import (
    ComposedArrayItems,
    NotConstraint,
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSchema,
    RawSection,
    RequirementCondition,
    ConditionalRequirement,
    SemanticConstraint,
    ValidationConstraint,
    WalkedArray,
    WalkedGroup,
    WalkedSchema,
    WalkedSection,
)
from draupnir.functions.pure.resolvers import (
    build_primitives_pool,
    collect_type_chain,
    resolve_composed_array,
    resolve_composed_array_items,
    resolve_thin_composed,
    resolve_structural_fields,
    resolve_type_chain,
    resolve_walked_array,
    resolve_walked_group,
    resolve_walked_schema,
    resolve_walked_section,
)


# =============================================================================
# FIXTURES — reusable primitive pools
# =============================================================================


def _make_pool() -> dict[str, RawPrimitive]:
    """Build a pool mimicking the real path type chain.

    Note: 'string' is a terminal JSON Schema type — no primitive needed for it.
    The chain is: path_exists_absolute → path_allowed_absolute → string (terminal).
    """
    path_allowed = RawPrimitive(
        name="path_allowed_absolute",
        type="string",
        requirement="inherit",
        format="path_allowed_absolute",
        pattern="^/",
        not_constraint=NotConstraint(ref="PATH_BLOCKLIST"),
        description="Allowed absolute path.",
    )
    path_exists = RawPrimitive(
        name="path_exists_absolute",
        type="path_allowed_absolute",
        requirement="inherit",
        format="path_exists_absolute",
        validation=ValidationConstraint(
            instruction="Must exist on filesystem.",
            severity="error",
        ),
        description="Path that must exist.",
    )
    dispatch_mode = RawPrimitive(
        name="dispatch_mode",
        type="string",
        requirement="mandatory",
        enum=("batch", "full"),
        description="Dispatch mode.",
    )
    instruction_text = RawPrimitive(
        name="instruction_text",
        type="string",
        requirement="required",
        semantic=SemanticConstraint(
            intent="Directs behavior.",
            checks=("check1",),
            severity="error",
        ),
        description="Instruction text.",
    )
    return build_primitives_pool([
        path_allowed, path_exists, dispatch_mode, instruction_text,
    ])


def _simple_pool() -> dict[str, RawPrimitive]:
    """Minimal pool: just a string base and one adopter."""
    base = RawPrimitive(
        name="agent_name",
        type="string",
        requirement="mandatory",
        description="Agent identifier.",
        pattern="^[a-z0-9]+(-[a-z0-9]+)*$",
    )
    return build_primitives_pool([base])


# =============================================================================
# PRIMITIVES POOL
# =============================================================================


class TestBuildPrimitivesPool:
    def test_indexes_by_name(self) -> None:
        p1 = RawPrimitive(
            name="agent_name", type="string",
            requirement="mandatory", description="Name.",
        )
        p2 = RawPrimitive(
            name="dispatch_mode", type="string",
            requirement="mandatory", description="Mode.",
        )
        pool = build_primitives_pool([p1, p2])
        assert "agent_name" in pool
        assert "dispatch_mode" in pool
        assert len(pool) == 2

    def test_empty_sequence(self) -> None:
        pool = build_primitives_pool([])
        assert pool == {}


# =============================================================================
# TYPE CHAIN
# =============================================================================


class TestCollectTypeChain:
    def test_single_level(self) -> None:
        """agent_name (type=string) → chain of 1."""
        pool = _simple_pool()
        chain = collect_type_chain("agent_name", pool)
        assert len(chain) == 1
        assert chain[0].name == "agent_name"

    def test_two_level(self) -> None:
        """path_allowed_absolute (type=string) → 1, but
        path_exists_absolute → path_allowed_absolute → string → 2.
        """
        pool = _make_pool()
        chain = collect_type_chain("path_exists_absolute", pool)
        assert len(chain) == 2
        assert chain[0].name == "path_exists_absolute"
        assert chain[1].name == "path_allowed_absolute"

    def test_unknown_type_raises(self) -> None:
        pool = _simple_pool()
        with pytest.raises(ValueError, match="Unknown primitive"):
            collect_type_chain("nonexistent", pool)

    def test_circular_raises(self) -> None:
        p1 = RawPrimitive(
            name="a", type="b", requirement="inherit", description="a",
        )
        p2 = RawPrimitive(
            name="b", type="a", requirement="inherit", description="b",
        )
        pool = build_primitives_pool([p1, p2])
        with pytest.raises(ValueError, match="Circular"):
            collect_type_chain("a", pool)


class TestResolveTypeChain:
    def test_single_level_properties(self) -> None:
        pool = _simple_pool()
        result = resolve_type_chain("agent_name", pool)
        assert result.json_type == "string"
        assert result.pattern == "^[a-z0-9]+(-[a-z0-9]+)*$"
        assert result.description == "Agent identifier."

    def test_two_level_override(self) -> None:
        """Shallowest format wins. Deeper pattern preserved."""
        pool = _make_pool()
        result = resolve_type_chain("path_exists_absolute", pool)
        assert result.json_type == "string"
        assert result.format == "path_exists_absolute"  # shallow wins
        assert result.pattern == "^/"  # from deeper level
        assert result.not_ref == "PATH_BLOCKLIST"  # from deeper
        assert result.validation.severity == "error"  # from shallow

    def test_enum_preserved(self) -> None:
        pool = _make_pool()
        result = resolve_type_chain("dispatch_mode", pool)
        assert result.enum_values == ("batch", "full")

    def test_semantic_preserved(self) -> None:
        pool = _make_pool()
        result = resolve_type_chain("instruction_text", pool)
        assert result.semantic is not None
        assert result.semantic.intent == "Directs behavior."


# =============================================================================
# COMPOSED FIELD RESOLUTION
# =============================================================================


class TestResolveThinComposed:
    def test_basic(self) -> None:
        pool = _simple_pool()
        composed = RawComposed(
            name="agent_name",
            type="agent_name",
            requirement="mandatory",
            description="The agent's name.",
        )
        field = resolve_thin_composed(composed, pool)
        assert field.name == "agent_name"
        assert field.json_type == "string"
        assert field.requirement == "mandatory"
        assert field.description == "The agent's name."  # composed overrides

    def test_composed_description_overrides_chain(self) -> None:
        pool = _make_pool()
        composed = RawComposed(
            name="workspace_path",
            type="path_exists_absolute",
            requirement="required",
            description="Workspace root.",
        )
        field = resolve_thin_composed(composed, pool)
        assert field.description == "Workspace root."  # from composed
        assert field.format == "path_exists_absolute"  # from chain

    def test_no_composed_description_uses_chain(self) -> None:
        pool = _make_pool()
        composed = RawComposed(
            name="workspace_path",
            type="path_exists_absolute",
            requirement="required",
        )
        field = resolve_thin_composed(composed, pool)
        assert field.description == "Path that must exist."  # from chain

    def test_conditional_requirement(self) -> None:
        pool = _make_pool()
        cond = RequirementCondition(
            only_when=ConditionalRequirement(
                field="dispatch_mode", equals="batch",
            ),
        )
        composed = RawComposed(
            name="batch_size",
            type="dispatch_mode",
            requirement=cond,
        )
        field = resolve_thin_composed(composed, pool)
        assert not isinstance(field.requirement, str)


class TestResolveStructuralFields:
    def test_resolves_field_dict(self) -> None:
        pool = _simple_pool()
        fields = resolve_structural_fields(
            {"name_field": "agent_name"}, pool,
        )
        assert len(fields) == 1
        assert fields[0].name == "name_field"
        assert fields[0].json_type == "string"


# =============================================================================
# WALKED → RESOLVED
# =============================================================================


class TestResolveWalkedGroup:
    def test_with_composed_fields(self) -> None:
        pool = _simple_pool()
        composed = RawComposed(
            name="agent_name", type="agent_name",
            requirement="mandatory",
        )
        raw_group = RawGroup(
            name="test_group", type="object",
            fields={"agent_name": "agent_name"},
        )
        walked = WalkedGroup(
            raw=raw_group,
            composed_fields=(composed,),
        )
        resolved = resolve_walked_group(walked, pool)
        assert resolved.name == "test_group"
        assert len(resolved.fields) == 1
        assert resolved.fields[0].json_type == "string"

    def test_with_sub_groups(self) -> None:
        pool = _simple_pool()
        child_composed = RawComposed(
            name="agent_name", type="agent_name",
            requirement="mandatory",
        )
        child_raw = RawGroup(name="child", type="object")
        child_walked = WalkedGroup(
            raw=child_raw, composed_fields=(child_composed,),
        )
        parent_raw = RawGroup(name="parent", type="object")
        parent_walked = WalkedGroup(
            raw=parent_raw, sub_groups=(child_walked,),
        )
        resolved = resolve_walked_group(parent_walked, pool)
        assert len(resolved.sub_groups) == 1
        assert resolved.sub_groups[0].name == "child"

    def test_metadata_preserved(self) -> None:
        pool = _simple_pool()
        raw_group = RawGroup(
            name="test", type="object",
            description="A test group.",
            composition="AllOf",
            additional_properties=True,
            required_fields=("agent_name",),
        )
        walked = WalkedGroup(raw=raw_group)
        resolved = resolve_walked_group(walked, pool)
        assert resolved.description == "A test group."
        assert resolved.composition == "AllOf"
        assert resolved.additional_properties is True
        assert resolved.required_fields == ("agent_name",)


class TestResolveWalkedArray:
    def test_single_item_type(self) -> None:
        pool = _simple_pool()
        item_raw = RawGroup(name="item", type="object")
        item_walked = WalkedGroup(raw=item_raw)
        raw_array = RawArray.model_validate(
            {"name": "entries", "type": "array", "items": {"$ref": "item"}},
        )
        walked = WalkedArray(raw=raw_array, items=(item_walked,))
        resolved = resolve_walked_array(walked, pool)
        assert resolved.name == "entries"
        assert len(resolved.items) == 1


class TestResolveWalkedSection:
    def test_with_components(self) -> None:
        pool = _simple_pool()
        comp_raw = RawGroup(name="paths", type="object")
        comp_walked = WalkedGroup(raw=comp_raw)
        raw_section = RawSection(
            name="security", type="object",
            composition="Mixed",
            required_fields=("paths",),
        )
        walked = WalkedSection(
            raw=raw_section, components=(comp_walked,),
        )
        resolved = resolve_walked_section(walked, pool)
        assert resolved.name == "security"
        assert len(resolved.components) == 1
        assert resolved.required_fields == ("paths",)


class TestResolveWalkedSectionWithArrays:
    def test_section_arrays_resolved(self) -> None:
        """WalkedSection with arrays → ResolvedSection with resolved arrays."""
        pool = _simple_pool()
        item_raw = RawGroup(name="criterion", type="object")
        item_walked = WalkedGroup(raw=item_raw)
        raw_array = RawArray.model_validate(
            {"name": "success_criteria", "type": "array", "items": {"$ref": "x"}},
        )
        walked_array = WalkedArray(raw=raw_array, items=(item_walked,))
        raw_section = RawSection(
            name="criteria",
            type="object",
            required_fields=("success_criteria",),
        )
        walked = WalkedSection(
            raw=raw_section,
            arrays=(walked_array,),
        )
        resolved = resolve_walked_section(walked, pool)
        assert len(resolved.arrays) == 1
        assert resolved.arrays[0].name == "success_criteria"

    def test_section_with_both(self) -> None:
        """Section with components AND arrays → both resolved."""
        pool = _simple_pool()
        comp_raw = RawGroup(name="paths", type="object")
        comp_walked = WalkedGroup(raw=comp_raw)
        item_raw = RawGroup(name="item", type="object")
        item_walked = WalkedGroup(raw=item_raw)
        raw_array = RawArray.model_validate(
            {"name": "entries", "type": "array", "items": {"$ref": "x"}},
        )
        walked_array = WalkedArray(raw=raw_array, items=(item_walked,))
        raw_section = RawSection(name="mixed", type="object")
        walked = WalkedSection(
            raw=raw_section,
            components=(comp_walked,),
            arrays=(walked_array,),
        )
        resolved = resolve_walked_section(walked, pool)
        assert len(resolved.components) == 1
        assert len(resolved.arrays) == 1


class TestResolveWalkedSchema:
    def test_full_resolution(self) -> None:
        pool = _simple_pool()
        # Build a minimal walked schema
        comp_raw = RawGroup(name="paths", type="object")
        comp_walked = WalkedGroup(raw=comp_raw)
        raw_section = RawSection(name="security", type="object")
        walked_section = WalkedSection(
            raw=raw_section, components=(comp_walked,),
        )
        raw_schema = RawSchema(
            name="agent-definition",
            version=3,
            description="Test schema.",
            required_sections=("security",),
        )
        walked = WalkedSchema(
            raw=raw_schema, sections=(walked_section,),
        )
        resolved = resolve_walked_schema(walked, pool)
        assert resolved.name == "agent-definition"
        assert resolved.version == 3
        assert len(resolved.sections) == 1
        assert resolved.sections[0].name == "security"


# =============================================================================
# COMPOSED ARRAY RESOLUTION
# =============================================================================


class TestResolveComposedArrayItems:
    def test_ref_items(self) -> None:
        """$ref to primitive → ResolvedField with chain-resolved properties."""
        pool = _make_pool()
        items = ComposedArrayItems(ref="dispatch_mode")
        result = resolve_composed_array_items(items, pool)
        assert result.json_type == "string"
        assert result.enum_values == ("batch", "full")

    def test_inline_type(self) -> None:
        """type=integer → ResolvedField(json_type='integer')."""
        pool = _simple_pool()
        items = ComposedArrayItems(type="integer")
        result = resolve_composed_array_items(items, pool)
        assert result.json_type == "integer"

    def test_neither_raises(self) -> None:
        """Neither ref nor type → ValueError."""
        pool = _simple_pool()
        items = ComposedArrayItems()
        with pytest.raises(ValueError, match="neither"):
            resolve_composed_array_items(items, pool)


class TestResolveComposedArray:
    def test_basic_ref_items(self) -> None:
        """Composed array with $ref items resolves correctly."""
        pool = _make_pool()
        composed = RawComposed(
            name="guardrails_constraints",
            type="array",
            requirement="mandatory",
            description="Behavioral constraints.",
            items=ComposedArrayItems(ref="instruction_text"),
            min_items=1,
            unique_items=True,
            semantic=SemanticConstraint(
                intent="Boundary.", severity="error",
            ),
        )
        result = resolve_composed_array(composed, pool)
        assert result.name == "guardrails_constraints"
        assert result.description == "Behavioral constraints."
        assert result.min_items == 1
        assert result.unique_items is True
        assert result.requirement == "mandatory"
        assert result.semantic is not None
        assert result.semantic.intent == "Boundary."
        # Items resolved to a field
        from draupnir.structures import ResolvedField
        assert isinstance(result.items, ResolvedField)
        assert result.items.json_type == "string"

    def test_inline_type_items(self) -> None:
        """Composed array with inline type items."""
        pool = _simple_pool()
        composed = RawComposed(
            name="batch_sizes",
            type="array",
            requirement="optional",
            items=ComposedArrayItems(type="integer"),
            max_items=10,
        )
        result = resolve_composed_array(composed, pool)
        assert result.name == "batch_sizes"
        from draupnir.structures import ResolvedField
        assert isinstance(result.items, ResolvedField)
        assert result.items.json_type == "integer"
        assert result.max_items == 10

    def test_conditional_requirement(self) -> None:
        """Composed array with conditional requirement preserved."""
        pool = _make_pool()
        cond = RequirementCondition(
            only_when=ConditionalRequirement(
                field="dispatch_mode", equals="batch",
            ),
        )
        composed = RawComposed(
            name="batch_sizes",
            type="array",
            requirement=cond,
            items=ComposedArrayItems(type="integer"),
        )
        result = resolve_composed_array(composed, pool)
        assert isinstance(result.requirement, RequirementCondition)

    def test_no_items_raises(self) -> None:
        """Composed array without items → ValueError."""
        pool = _simple_pool()
        composed = RawComposed(
            name="bad_array",
            type="array",
            requirement="optional",
        )
        with pytest.raises(ValueError, match="no items"):
            resolve_composed_array(composed, pool)

    def test_name_stabilized(self) -> None:
        """Composed array name gets stabilized."""
        pool = _simple_pool()
        composed = RawComposed(
            name="constraints_resolved",
            type="array",
            requirement="optional",
            items=ComposedArrayItems(type="string"),
        )
        result = resolve_composed_array(composed, pool)
        assert result.name == "constraints"


class TestResolveGroupWithComposedArrays:
    def test_composed_arrays_in_group(self) -> None:
        """WalkedGroup with composed_arrays → ResolvedGroup with arrays."""
        pool = _make_pool()
        composed_arr = RawComposed(
            name="constraints",
            type="array",
            requirement="mandatory",
            items=ComposedArrayItems(ref="instruction_text"),
        )
        raw_group = RawGroup(name="guardrails", type="object")
        walked = WalkedGroup(
            raw=raw_group,
            composed_arrays=(composed_arr,),
        )
        resolved = resolve_walked_group(walked, pool)
        assert len(resolved.arrays) == 1
        assert resolved.arrays[0].name == "constraints"
        assert resolved.arrays[0].requirement == "mandatory"

    def test_file_and_composed_arrays_combined(self) -> None:
        """Group with both file-ref and composed arrays."""
        pool = _simple_pool()
        # File-ref array
        item_raw = RawGroup(name="item", type="object")
        item_walked = WalkedGroup(raw=item_raw)
        raw_array = RawArray.model_validate(
            {"name": "entries", "type": "array", "items": {"$ref": "x"}},
        )
        walked_array = WalkedArray(raw=raw_array, items=(item_walked,))
        # Composed array
        composed_arr = RawComposed(
            name="sizes",
            type="array",
            requirement="optional",
            items=ComposedArrayItems(type="integer"),
        )
        raw_group = RawGroup(name="parent", type="object")
        walked = WalkedGroup(
            raw=raw_group,
            arrays=(walked_array,),
            composed_arrays=(composed_arr,),
        )
        resolved = resolve_walked_group(walked, pool)
        assert len(resolved.arrays) == 2
        names = {a.name for a in resolved.arrays}
        assert names == {"entries", "sizes"}


# =============================================================================
# NAME STABILIZATION
# =============================================================================


class TestNameStabilization:
    def test_group_name_stabilized(self) -> None:
        pool = _simple_pool()
        raw_group = RawGroup(
            name="security_resolved", type="object",
        )
        walked = WalkedGroup(raw=raw_group)
        resolved = resolve_walked_group(walked, pool)
        assert resolved.name == "security"

    def test_array_name_stabilized(self) -> None:
        pool = _simple_pool()
        item_raw = RawGroup(name="item", type="object")
        item_walked = WalkedGroup(raw=item_raw)
        raw_array = RawArray.model_validate(
            {"name": "entries_reduced", "type": "array", "items": {"$ref": "x"}},
        )
        walked = WalkedArray(raw=raw_array, items=(item_walked,))
        resolved = resolve_walked_array(walked, pool)
        assert resolved.name == "entries"

    def test_section_name_stabilized(self) -> None:
        pool = _simple_pool()
        raw_section = RawSection(
            name="criteria_resolved", type="object",
        )
        walked = WalkedSection(raw=raw_section)
        resolved = resolve_walked_section(walked, pool)
        assert resolved.name == "criteria"

    def test_composed_name_stabilized(self) -> None:
        pool = _simple_pool()
        composed = RawComposed(
            name="context_path_resolved",
            type="agent_name",
            requirement="required",
        )
        field = resolve_thin_composed(composed, pool)
        assert field.name == "context_path"
