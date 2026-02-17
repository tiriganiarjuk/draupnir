"""Tests for draupnir.functions.pure.walkers — tree walking with mock IO."""

from pathlib import PurePosixPath

import pytest

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawSchema,
    RawSection,
    SchemaLoaders,
)
from draupnir.structures import RefString
from draupnir.functions.pure.walkers import (
    is_blocklist_composed,
    walk_array,
    walk_group,
    walk_schema,
    walk_section,
)


ROOT = PurePosixPath("/fake/toolcompose")


def make_loaders(file_map: dict[str, dict]) -> SchemaLoaders:
    """Create mock SchemaLoaders that validate dicts from file_map."""

    def _load_or_raise(path: PurePosixPath, model_class: type):
        key = str(path)
        if key not in file_map:
            raise FileNotFoundError(f"Mock: {key}")
        return model_class.model_validate(file_map[key])

    return SchemaLoaders(
        composed=lambda p: _load_or_raise(p, RawComposed),
        group=lambda p: _load_or_raise(p, RawGroup),
        array=lambda p: _load_or_raise(p, RawArray),
        section=lambda p: _load_or_raise(p, RawSection),
    )


# =============================================================================
# GROUP WALKING
# =============================================================================


class TestWalkGroup:
    def test_loads_thin_composed_fields(self) -> None:
        """Group with two thin composed fields."""
        raw_group = RawGroup(
            name="test_group",
            type="object",
            fields={
                "field_a": "composed/field_a.yaml",
                "field_b": "composed/field_b.yaml",
            },
        )
        file_map = {
            "/fake/toolcompose/composed/field_a.yaml": {
                "name": "field_a",
                "type": "path_allowed_any",
                "requirement": "required",
                "description": "Field A.",
            },
            "/fake/toolcompose/composed/field_b.yaml": {
                "name": "field_b",
                "type": "string",
                "requirement": "optional",
                "description": "Field B.",
            },
        }
        walked = walk_group(raw_group, ROOT, make_loaders(file_map))
        assert len(walked.composed_fields) == 2
        assert walked.composed_fields[0].name == "field_a"
        assert walked.sub_groups == ()

    def test_structural_composed_becomes_sub_group(self) -> None:
        """Structural composed (type=object) becomes a sub-group."""
        raw_group = RawGroup(
            name="parent",
            type="object",
            fields={"nested": "composed/nested.yaml"},
        )
        file_map = {
            "/fake/toolcompose/composed/nested.yaml": {
                "name": "nested",
                "type": "object",
                "requirement": "required",
                "description": "Nested object.",
                "composition": "AllOf",
                "additional_properties": False,
                "fields": {"include": "path_exists_absolute"},
            },
        }
        walked = walk_group(raw_group, ROOT, make_loaders(file_map))
        assert len(walked.composed_fields) == 0
        assert len(walked.sub_groups) == 1
        assert walked.sub_groups[0].raw.name == "nested"

    def test_with_arrays(self) -> None:
        """Group (supergroup) with an array reference."""
        raw_group = RawGroup(
            name="context",
            type="object",
            arrays={"entries": "arrays/entries.yaml"},
        )
        file_map = {
            "/fake/toolcompose/arrays/entries.yaml": {
                "name": "entries",
                "type": "array",
                "items": {"$ref": "groups/entry_item.yaml"},
            },
            "/fake/toolcompose/groups/entry_item.yaml": {
                "name": "entry_item",
                "type": "object",
                "fields": {},
            },
        }
        walked = walk_group(raw_group, ROOT, make_loaders(file_map))
        assert len(walked.arrays) == 1
        assert walked.arrays[0].raw.name == "entries"
        assert len(walked.arrays[0].items) == 1

    def test_empty_group(self) -> None:
        """Group with no fields or arrays."""
        raw_group = RawGroup(name="empty", type="object")
        walked = walk_group(raw_group, ROOT, make_loaders({}))
        assert walked.composed_fields == ()
        assert walked.sub_groups == ()
        assert walked.arrays == ()

    def test_blocklist_composed_skipped(self) -> None:
        """Blocklist composed (no type, has imports) is skipped entirely."""
        raw_group = RawGroup(
            name="parent",
            type="object",
            fields={"blocklist": "composed/blocklist.yaml"},
        )
        file_map = {
            "/fake/toolcompose/composed/blocklist.yaml": {
                "name": "PATH_BLOCKLIST",
                "description": "Forbidden path patterns.",
                "imports": [
                    {"$ref": "path_forbidden_root"},
                    {"$ref": "path_forbidden_home"},
                ],
            },
        }
        walked = walk_group(raw_group, ROOT, make_loaders(file_map))
        assert walked.composed_fields == ()
        assert walked.sub_groups == ()
        assert walked.composed_arrays == ()


    def test_composed_array_classified(self) -> None:
        """Composed array (type=array) goes to composed_arrays, not fields."""
        raw_group = RawGroup(
            name="parent",
            type="object",
            fields={"constraints": "composed/constraints.yaml"},
        )
        file_map = {
            "/fake/toolcompose/composed/constraints.yaml": {
                "name": "constraints",
                "type": "array",
                "requirement": "mandatory",
                "description": "Behavioral constraints.",
                "items": {"$ref": "guardrails_constraint"},
                "minItems": 1,
            },
        }
        walked = walk_group(raw_group, ROOT, make_loaders(file_map))
        assert len(walked.composed_fields) == 0
        assert len(walked.sub_groups) == 0
        assert len(walked.composed_arrays) == 1
        assert walked.composed_arrays[0].name == "constraints"
        assert walked.composed_arrays[0].type == "array"

    def test_mixed_composed_types(self) -> None:
        """Group with thin, structural, array, and blocklist composed fields."""
        raw_group = RawGroup(
            name="parent",
            type="object",
            fields={
                "thin": "composed/thin.yaml",
                "structural": "composed/structural.yaml",
                "arr": "composed/arr.yaml",
                "blocklist": "composed/blocklist.yaml",
            },
        )
        file_map = {
            "/fake/toolcompose/composed/thin.yaml": {
                "name": "thin",
                "type": "string",
                "requirement": "required",
            },
            "/fake/toolcompose/composed/structural.yaml": {
                "name": "structural",
                "type": "object",
                "requirement": "required",
                "composition": "AllOf",
                "additional_properties": False,
                "fields": {"include": "path_exists_absolute"},
            },
            "/fake/toolcompose/composed/arr.yaml": {
                "name": "arr",
                "type": "array",
                "requirement": "optional",
                "items": {"type": "integer"},
            },
            "/fake/toolcompose/composed/blocklist.yaml": {
                "name": "PATH_BLOCKLIST",
                "description": "Forbidden.",
                "imports": [{"$ref": "path_forbidden"}],
            },
        }
        walked = walk_group(raw_group, ROOT, make_loaders(file_map))
        assert len(walked.composed_fields) == 1  # thin
        assert len(walked.sub_groups) == 1  # structural
        assert len(walked.composed_arrays) == 1  # arr
        # blocklist is skipped entirely


class TestIsBlocklistComposed:
    def test_blocklist_detected(self) -> None:
        """Composed with no type and imports is blocklist."""
        composed = RawComposed(
            name="PATH_BLOCKLIST",
            description="Forbidden patterns.",
            imports=(
                RefString(ref="path_forbidden_root"),
                RefString(ref="path_forbidden_home"),
            ),
        )
        assert is_blocklist_composed(composed) is True

    def test_thin_not_blocklist(self) -> None:
        composed = RawComposed(
            name="field_a", type="string", requirement="required",
        )
        assert is_blocklist_composed(composed) is False


# =============================================================================
# ARRAY WALKING
# =============================================================================


class TestWalkArray:
    def test_single_ref_item(self) -> None:
        """Array with single $ref item type."""
        raw_array = RawArray.model_validate({
            "name": "context_required",
            "type": "array",
            "items": {"$ref": "groups/context_item.yaml"},
        })
        file_map = {
            "/fake/toolcompose/groups/context_item.yaml": {
                "name": "context_item",
                "type": "object",
                "fields": {},
            },
        }
        walked = walk_array(raw_array, ROOT, make_loaders(file_map))
        assert len(walked.items) == 1
        assert walked.items[0].raw.name == "context_item"

    def test_one_of_items(self) -> None:
        """Array with oneOf union item types."""
        raw_array = RawArray.model_validate({
            "name": "example_entries",
            "type": "array",
            "items": {
                "oneOf": [
                    {"$ref": "groups/entry.yaml"},
                    {"$ref": "groups/include.yaml"},
                ],
            },
        })
        file_map = {
            "/fake/toolcompose/groups/entry.yaml": {
                "name": "entry",
                "type": "object",
                "fields": {},
            },
            "/fake/toolcompose/groups/include.yaml": {
                "name": "include",
                "type": "object",
                "fields": {},
            },
        }
        walked = walk_array(raw_array, ROOT, make_loaders(file_map))
        assert len(walked.items) == 2


# =============================================================================
# SECTION WALKING
# =============================================================================


class TestWalkSection:
    def test_loads_sub_components(self) -> None:
        raw_section = RawSection(
            name="security",
            type="object",
            sub_components={
                "security_paths": "groups/security_paths.yaml",
            },
        )
        file_map = {
            "/fake/toolcompose/groups/security_paths.yaml": {
                "name": "security_paths",
                "type": "object",
                "fields": {},
            },
        }
        walked = walk_section(
            raw_section, ROOT, make_loaders(file_map),
        )
        assert len(walked.components) == 1
        assert walked.components[0].raw.name == "security_paths"

    def test_section_with_arrays(self) -> None:
        """Section with arrays dict → WalkedSection.arrays populated."""
        raw_section = RawSection(
            name="criteria",
            type="object",
            arrays={
                "success_criteria": "arrays/success_criteria.yaml",
            },
        )
        file_map = {
            "/fake/toolcompose/arrays/success_criteria.yaml": {
                "name": "success_criteria",
                "type": "array",
                "items": {"$ref": "groups/criterion.yaml"},
            },
            "/fake/toolcompose/groups/criterion.yaml": {
                "name": "criterion",
                "type": "object",
                "fields": {},
            },
        }
        walked = walk_section(
            raw_section, ROOT, make_loaders(file_map),
        )
        assert len(walked.arrays) == 1
        assert walked.arrays[0].raw.name == "success_criteria"

    def test_section_with_components_and_arrays(self) -> None:
        """Section with both sub_components and arrays."""
        raw_section = RawSection(
            name="execution",
            type="object",
            sub_components={
                "dispatch": "groups/dispatch.yaml",
            },
            arrays={
                "instructions": "arrays/instructions.yaml",
            },
        )
        file_map = {
            "/fake/toolcompose/groups/dispatch.yaml": {
                "name": "dispatch",
                "type": "object",
                "fields": {},
            },
            "/fake/toolcompose/arrays/instructions.yaml": {
                "name": "instructions",
                "type": "array",
                "items": {"$ref": "groups/instruction_item.yaml"},
            },
            "/fake/toolcompose/groups/instruction_item.yaml": {
                "name": "instruction_item",
                "type": "object",
                "fields": {},
            },
        }
        walked = walk_section(
            raw_section, ROOT, make_loaders(file_map),
        )
        assert len(walked.components) == 1
        assert len(walked.arrays) == 1

    def test_empty_section(self) -> None:
        raw_section = RawSection(name="empty", type="object")
        walked = walk_section(
            raw_section, ROOT, make_loaders({}),
        )
        assert walked.components == ()
        assert walked.arrays == ()


# =============================================================================
# SCHEMA WALKING
# =============================================================================


class TestWalkSchema:
    def test_full_walk(self) -> None:
        """Walk a schema with one section containing one group."""
        raw_schema = RawSchema(
            name="test-schema",
            version=1,
            description="Test.",
            sections={
                "security": "sections/security.yaml",
            },
            required_sections=("security",),
        )
        file_map = {
            "/fake/toolcompose/sections/security.yaml": {
                "name": "security",
                "type": "object",
                "sub_components": {
                    "paths": "groups/paths.yaml",
                },
            },
            "/fake/toolcompose/groups/paths.yaml": {
                "name": "paths",
                "type": "object",
                "fields": {
                    "workspace": "composed/workspace.yaml",
                },
            },
            "/fake/toolcompose/composed/workspace.yaml": {
                "name": "workspace",
                "type": "path_allowed_any",
                "requirement": "required",
                "description": "Workspace path.",
            },
        }
        walked = walk_schema(
            raw_schema, ROOT, make_loaders(file_map),
        )
        assert len(walked.sections) == 1
        section = walked.sections[0]
        assert section.raw.name == "security"
        assert len(section.components) == 1
        group = section.components[0]
        assert group.raw.name == "paths"
        assert len(group.composed_fields) == 1
        assert group.composed_fields[0].name == "workspace"

    def test_empty_schema(self) -> None:
        raw_schema = RawSchema(
            name="empty", version=1, description="Empty.",
        )
        walked = walk_schema(
            raw_schema, ROOT, make_loaders({}),
        )
        assert walked.sections == ()

    def test_missing_file_raises(self) -> None:
        raw_schema = RawSchema(
            name="test", version=1, description="Test.",
            sections={"missing": "sections/missing.yaml"},
        )
        with pytest.raises(FileNotFoundError):
            walk_schema(
                raw_schema, ROOT, make_loaders({}),
            )
