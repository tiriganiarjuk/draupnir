"""Tests for complex container and top-level models."""

import pytest
from pydantic import ValidationError

from draupnir.structures.complex_containers import (
    Array,
    ArrayOneOf,
    Group,
    GroupContainerConditionalEntry,
    GroupContainers,
    GroupFieldConditionalEntry,
    GroupFields,
    Superarray,
    SuperarrayOneOf,
)
from draupnir.structures.fields import Atom, Element, Enum, Pattern, Union_
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    Tuple_,
    VerdandiField,
)
from draupnir.structures.top_level import (
    Schema,
    Section,
    ShallowContainers,
    ShallowFieldConditionalEntry,
    Shallowsection,
)


@pytest.fixture
def cache():
    """Build a full cache with all tiers for complex container tests."""
    # Field-level models
    atom_str = Atom.model_validate(
        {"title": "Str", "type": "string", "description": "plain string"},
        context={"cache": {}},
    )
    atom_int = Atom.model_validate(
        {"title": "Int", "type": "integer", "description": "integer"},
        context={"cache": {}},
    )
    enum_mode = Enum(title="Mode", values=("batch", "full"), description="mode")
    pattern_rel = Pattern(title="Relative", regex=r"^\.", description="relative")
    union_path = Union_.model_validate(
        {
            "title": "PathAny",
            "union": ["atom/str", "atom/int"],
            "description": "path any",
        },
        context={
            "cache": {"atom/str": atom_str, "atom/int": atom_int},
        },
    )
    element_name = Element.model_validate(
        {
            "title": "AgentName",
            "inherits": "atom/str",
            "format": "kebab-case",
            "description": "agent name",
        },
        context={"cache": {"atom/str": atom_str}},
    )

    # VerdandiField wrappers (containers see field membrane, not raw types)
    field_str = VerdandiField(
        title="FieldStr", type=atom_str, description="a string field",
    )
    field_int = VerdandiField(
        title="FieldInt", type=atom_int, description="an integer field",
    )
    field_mode = VerdandiField(
        title="FieldMode", type=enum_mode, description="a mode field",
    )

    base = {
        "atom/str": atom_str,
        "atom/int": atom_int,
        "enum/mode": enum_mode,
        "pattern/rel": pattern_rel,
        "union/path": union_path,
        "element/name": element_name,
        "field/str": field_str,
        "field/int": field_int,
        "field/mode": field_mode,
    }

    # Simple containers
    tup = Tuple_.model_validate(
        {
            "title": "BatchSize",
            "items": ["atom/int", "atom/int"],
            "constraint": "ascending_strict",
            "description": "batch size",
        },
        context={"cache": base},
    )
    sa = Simplearray.model_validate(
        {"title": "StringList", "items": "field/str", "description": "string list"},
        context={"cache": base},
    )
    sg_param = Simplegroup.model_validate(
        {
            "title": "ParameterItem",
            "description": "parameter item",
            "required": {"name": "field/str", "value": "field/str"},
        },
        context={"cache": base},
    )
    sg_success = Simplegroup.model_validate(
        {
            "title": "SuccessItem",
            "description": "success item",
            "required": {"criterion": "field/str"},
            "optional": {"weight": "field/int"},
        },
        context={"cache": base},
    )
    sg_include = Simplegroup.model_validate(
        {
            "title": "IncludeSuccess",
            "description": "include success",
            "required": {"include": "field/str"},
        },
        context={"cache": base},
    )

    base["tuple/batch"] = tup
    base["simplearray/strings"] = sa
    base["simplegroup/param"] = sg_param
    base["simplegroup/success"] = sg_success
    base["simplegroup/include"] = sg_include

    # Arrays
    arr_simple = Array.model_validate(
        {
            "title": "ParameterArray",
            "items": "simplegroup/param",
            "description": "parameter array",
        },
        context={"cache": base},
    )
    arr_oneof = Array.model_validate(
        {
            "title": "CriteriaArray",
            "items": {"oneOf": ["simplegroup/success", "simplegroup/include"]},
            "description": "criteria array",
        },
        context={"cache": base},
    )

    base["array/params"] = arr_simple
    base["array/criteria"] = arr_oneof

    # Groups
    grp_meta = Group.model_validate(
        {
            "title": "Metadata",
            "description": "metadata",
            "fields": {
                "required": {"name": "field/str"},
            },
        },
        context={"cache": base},
    )
    grp_exec = Group.model_validate(
        {
            "title": "Execution",
            "description": "execution config",
            "fields": {
                "required": {"mode": "field/mode"},
            },
            "containers": {
                "required": {"params": "array/params"},
            },
        },
        context={"cache": base},
    )

    base["group/meta"] = grp_meta
    base["group/exec"] = grp_exec

    # Superarray
    sarr = Superarray.model_validate(
        {
            "title": "ExecExamples",
            "items": "group/exec",
            "description": "execution examples",
        },
        context={"cache": base},
    )

    base["superarray/examples"] = sarr

    # Sections
    sect_indirect = Section.model_validate(
        {
            "title": "Indirect",
            "description": "indirect section",
            "containers": {
                "required": {
                    "meta": "group/meta",
                    "params": "array/params",
                },
            },
        },
        context={"cache": base},
    )
    sect_exec = Section.model_validate(
        {
            "title": "Exec",
            "description": "execution section",
            "containers": {
                "required": {
                    "exec": "group/exec",
                    "examples": "superarray/examples",
                },
            },
        },
        context={"cache": base},
    )

    base["section/indirect"] = sect_indirect
    base["section/exec"] = sect_exec

    # Shallowsections
    shallow_dispatcher = Shallowsection.model_validate(
        {
            "title": "Dispatcher",
            "description": "dispatcher config",
            "required": {"mode": "field/mode"},
            "optional": {"name": "field/str"},
        },
        context={"cache": base},
    )

    base["shallowsection/dispatcher"] = shallow_dispatcher

    return base


# --- Array tests ---


class TestArray:
    def test_string_ref_resolves_to_simplegroup(self, cache):
        arr = Array.model_validate(
            {
                "title": "Test",
                "items": "simplegroup/param",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert arr.items is cache["simplegroup/param"]

    def test_oneof_resolves_to_array_oneof(self, cache):
        arr = Array.model_validate(
            {
                "title": "Test",
                "items": {
                    "oneOf": ["simplegroup/success", "simplegroup/include"],
                },
                "description": "test",
            },
            context={"cache": cache},
        )
        assert isinstance(arr.items, ArrayOneOf)
        assert arr.items.one_of[0] is cache["simplegroup/success"]
        assert arr.items.one_of[1] is cache["simplegroup/include"]

    def test_rejects_group_ref_in_items(self, cache):
        with pytest.raises(ValidationError):
            Array.model_validate(
                {
                    "title": "Test",
                    "items": "group/meta",
                    "description": "test",
                },
                context={"cache": cache},
            )


# --- Group field conditional tests ---


class TestGroupFieldConditional:
    def test_accepts_field_ref(self, cache):
        entry = GroupFieldConditionalEntry.model_validate(
            {
                "ref": "field/str",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["field/str"]

    def test_accepts_another_field_ref(self, cache):
        entry = GroupFieldConditionalEntry.model_validate(
            {
                "ref": "field/int",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["field/int"]

    def test_rejects_no_condition(self, cache):
        with pytest.raises(ValidationError):
            GroupFieldConditionalEntry.model_validate(
                {"ref": "field/str"},
                context={"cache": cache},
            )


# --- Group container conditional tests ---


class TestGroupContainerConditional:
    def test_accepts_array_ref(self, cache):
        entry = GroupContainerConditionalEntry.model_validate(
            {
                "ref": "array/params",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["array/params"]

    def test_rejects_group_ref(self, cache):
        with pytest.raises(ValidationError):
            GroupContainerConditionalEntry.model_validate(
                {
                    "ref": "group/meta",
                    "only_when": {"field": "mode", "equals": "batch"},
                },
                context={"cache": cache},
            )


# --- GroupFields tests ---


class TestGroupFields:
    def test_all_zones(self, cache):
        gf = GroupFields.model_validate(
            {
                "required": {"name": "field/str"},
                "optional": {"count": "field/int"},
            },
            context={"cache": cache},
        )
        assert gf.required is not None
        assert gf.optional is not None


# --- GroupContainers tests ---


class TestGroupContainers:
    def test_required_and_optional(self, cache):
        gc = GroupContainers.model_validate(
            {
                "required": {"params": "array/params"},
                "optional": {"extra": "simplegroup/param"},
            },
            context={"cache": cache},
        )
        assert gc.required is not None
        assert gc.optional is not None


# --- Superarray tests ---


class TestSuperarray:
    def test_string_ref_to_group(self, cache):
        sarr = Superarray.model_validate(
            {
                "title": "Test",
                "items": "group/exec",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert sarr.items is cache["group/exec"]

    def test_string_ref_to_simplegroup(self, cache):
        sarr = Superarray.model_validate(
            {
                "title": "Test",
                "items": "simplegroup/param",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert sarr.items is cache["simplegroup/param"]

    def test_oneof_resolves_to_superarray_oneof(self, cache):
        sarr = Superarray.model_validate(
            {
                "title": "Test",
                "items": {
                    "oneOf": ["group/exec", "simplegroup/param"],
                },
                "description": "test",
            },
            context={"cache": cache},
        )
        assert isinstance(sarr.items, SuperarrayOneOf)

    def test_rejects_array_ref_in_items(self, cache):
        with pytest.raises(ValidationError):
            Superarray.model_validate(
                {
                    "title": "Test",
                    "items": "array/params",
                    "description": "test",
                },
                context={"cache": cache},
            )


# --- Section tests ---


class TestSection:
    def test_containers_accept_group(self, cache):
        sect = Section.model_validate(
            {
                "title": "Test",
                "description": "test",
                "containers": {"required": {"meta": "group/meta"}},
            },
            context={"cache": cache},
        )
        assert sect.containers.required["meta"] is cache["group/meta"]

    def test_containers_accept_array(self, cache):
        sect = Section.model_validate(
            {
                "title": "Test",
                "description": "test",
                "containers": {"required": {"params": "array/params"}},
            },
            context={"cache": cache},
        )
        assert sect.containers.required["params"] is cache["array/params"]

    def test_containers_accept_superarray(self, cache):
        sect = Section.model_validate(
            {
                "title": "Test",
                "description": "test",
                "containers": {"required": {"examples": "superarray/examples"}},
            },
            context={"cache": cache},
        )
        assert sect.containers.required["examples"] is cache["superarray/examples"]

    def test_rejects_simplegroup_in_containers(self, cache):
        with pytest.raises(ValidationError):
            Section.model_validate(
                {
                    "title": "Test",
                    "description": "test",
                    "containers": {"required": {"bad": "simplegroup/param"}},
                },
                context={"cache": cache},
            )

    def test_rejects_field_in_containers(self, cache):
        with pytest.raises(ValidationError):
            Section.model_validate(
                {
                    "title": "Test",
                    "description": "test",
                    "containers": {"required": {"bad": "field/str"}},
                },
                context={"cache": cache},
            )


# --- Shallowsection tests ---


class TestShallowsection:
    def test_fields_and_containers(self, cache):
        ss = Shallowsection.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {"name": "field/str"},
                "containers": {
                    "required": {"params": "array/params"},
                },
            },
            context={"cache": cache},
        )
        assert ss.required is not None
        assert ss.containers is not None

    def test_fields_only(self, cache):
        ss = Shallowsection.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {"name": "field/str"},
            },
            context={"cache": cache},
        )
        assert ss.containers is None

    def test_max_two_containers(self, cache):
        ss = Shallowsection.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {"name": "field/str"},
                "containers": {
                    "required": {
                        "params": "array/params",
                        "criteria": "array/criteria",
                    },
                },
            },
            context={"cache": cache},
        )
        assert len(ss.containers.required) == 2

    def test_rejects_three_containers(self, cache):
        with pytest.raises(ValidationError):
            Shallowsection.model_validate(
                {
                    "title": "Test",
                    "description": "test",
                    "required": {"name": "field/str"},
                    "containers": {
                        "required": {
                            "a": "array/params",
                            "b": "array/criteria",
                            "c": "simplearray/strings",
                        },
                    },
                },
                context={"cache": cache},
            )


# --- ShallowFieldConditional tests ---


class TestShallowFieldConditional:
    def test_accepts_field_int_ref(self, cache):
        entry = ShallowFieldConditionalEntry.model_validate(
            {
                "ref": "field/int",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["field/int"]

    def test_accepts_field_str_ref(self, cache):
        entry = ShallowFieldConditionalEntry.model_validate(
            {
                "ref": "field/str",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["field/str"]

    def test_rejects_array_ref(self, cache):
        with pytest.raises(ValidationError):
            ShallowFieldConditionalEntry.model_validate(
                {
                    "ref": "array/params",
                    "only_when": {"field": "mode", "equals": "batch"},
                },
                context={"cache": cache},
            )


# --- Schema tests ---


class TestSchema:
    def test_sections_schema(self, cache):
        schema = Schema.model_validate(
            {
                "title": "RawDefinition",
                "version": 3,
                "description": "raw definition",
                "required": ["indirect", "exec"],
                "sections": {
                    "indirect": "section/indirect",
                    "exec": "section/exec",
                },
            },
            context={"cache": cache},
        )
        assert schema.sections is not None
        assert schema.shallowsections is None
        assert schema.sections["indirect"] is cache["section/indirect"]

    def test_shallowsections_schema(self, cache):
        schema = Schema.model_validate(
            {
                "title": "RenderSchema",
                "version": 1,
                "description": "render schema",
                "required": ["dispatcher"],
                "shallowsections": {
                    "dispatcher": "shallowsection/dispatcher",
                },
            },
            context={"cache": cache},
        )
        assert schema.shallowsections is not None
        assert schema.sections is None

    def test_rejects_both_sections_and_shallowsections(self, cache):
        with pytest.raises(ValidationError, match="mutually exclusive"):
            Schema.model_validate(
                {
                    "title": "Test",
                    "version": 1,
                    "description": "test",
                    "sections": {"indirect": "section/indirect"},
                    "shallowsections": {
                        "dispatcher": "shallowsection/dispatcher",
                    },
                },
                context={"cache": cache},
            )

    def test_rejects_neither_sections_nor_shallowsections(self, cache):
        with pytest.raises(ValidationError):
            Schema.model_validate(
                {
                    "title": "Test",
                    "version": 1,
                    "description": "test",
                },
                context={"cache": cache},
            )

    def test_nullable_field(self, cache):
        schema = Schema.model_validate(
            {
                "title": "NullableTest",
                "version": 1,
                "description": "nullable test",
                "nullable": ["exec"],
                "sections": {
                    "indirect": "section/indirect",
                    "exec": "section/exec",
                },
            },
            context={"cache": cache},
        )
        assert schema.nullable == ("exec",)

    def test_is_frozen(self, cache):
        schema = Schema.model_validate(
            {
                "title": "FrozenTest",
                "version": 1,
                "description": "test",
                "sections": {"indirect": "section/indirect"},
            },
            context={"cache": cache},
        )
        with pytest.raises(ValidationError):
            schema.version = 2  # type: ignore[misc]
