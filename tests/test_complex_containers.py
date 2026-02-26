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
        {"type": "string", "description": "plain string"},
        context={"cache": {}},
    )
    atom_int = Atom.model_validate(
        {"type": "integer", "description": "integer"},
        context={"cache": {}},
    )
    enum_mode = Enum(values=("batch", "full"), description="mode")
    pattern_rel = Pattern(regex=r"^\.", description="relative")
    union_path = Union_.model_validate(
        {"union": ["atom/str", "atom/int"], "description": "path any"},
        context={
            "cache": {"atom/str": atom_str, "atom/int": atom_int},
        },
    )
    element_name = Element.model_validate(
        {
            "inherits": "atom/str",
            "format": "kebab-case",
            "description": "agent name",
        },
        context={"cache": {"atom/str": atom_str}},
    )

    base = {
        "atom/str": atom_str,
        "atom/int": atom_int,
        "enum/mode": enum_mode,
        "pattern/rel": pattern_rel,
        "union/path": union_path,
        "element/name": element_name,
    }

    # Simple containers
    tup = Tuple_.model_validate(
        {
            "items": ["atom/int", "atom/int"],
            "constraint": "ascending_strict",
            "description": "batch size",
        },
        context={"cache": base},
    )
    sa = Simplearray.model_validate(
        {"items": "atom/str", "description": "string list"},
        context={"cache": base},
    )
    sg_param = Simplegroup.model_validate(
        {
            "description": "parameter item",
            "required": {"name": "atom/str", "value": "atom/str"},
        },
        context={"cache": base},
    )
    sg_success = Simplegroup.model_validate(
        {
            "description": "success item",
            "required": {"criterion": "atom/str"},
            "optional": {"weight": "atom/int"},
        },
        context={"cache": base},
    )
    sg_include = Simplegroup.model_validate(
        {
            "description": "include success",
            "required": {"include": "atom/str"},
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
            "items": "simplegroup/param",
            "description": "parameter array",
        },
        context={"cache": base},
    )
    arr_oneof = Array.model_validate(
        {
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
            "description": "metadata",
            "fields": {
                "required": {"name": "atom/str"},
            },
        },
        context={"cache": base},
    )
    grp_dispatch = Group.model_validate(
        {
            "description": "dispatch config",
            "fields": {
                "required": {"mode": "enum/mode"},
                "conditional": {
                    "batch_size": {
                        "ref": "tuple/batch",
                        "only_when": {
                            "field": "mode",
                            "equals": "batch",
                        },
                    },
                },
            },
            "containers": {
                "optional": {"parameters": "array/params"},
            },
        },
        context={"cache": base},
    )

    base["group/meta"] = grp_meta
    base["group/dispatch"] = grp_dispatch

    # Superarray
    sup = Superarray.model_validate(
        {
            "items": {
                "oneOf": ["group/meta", "simplegroup/include"],
            },
            "description": "example groups",
        },
        context={"cache": base},
    )
    base["superarray/examples"] = sup

    # Sections
    sec_indirect = Section.model_validate(
        {
            "description": "system metadata",
            "components": {
                "metadata": "group/meta",
                "dispatch": "group/dispatch",
            },
        },
        context={"cache": base},
    )
    sec_exec = Section.model_validate(
        {
            "description": "execution",
            "components": {"criteria": "array/criteria"},
        },
        context={"cache": base},
    )

    base["section/indirect"] = sec_indirect
    base["section/exec"] = sec_exec

    # Shallowsection
    shallow = Shallowsection.model_validate(
        {
            "description": "dispatcher view",
            "required": {"name": "element/name", "mode": "enum/mode"},
            "optional": {"max_agents": "atom/int"},
            "conditional": {
                "batch_size": {
                    "ref": "tuple/batch",
                    "only_when": {
                        "field": "mode",
                        "equals": "batch",
                    },
                },
            },
            "containers": {
                "optional": {"parameters": "array/params"},
            },
        },
        context={"cache": base},
    )
    base["shallowsection/dispatcher"] = shallow

    return base


# --- Array tests ---


class TestArray:
    def test_string_ref_resolves_to_simplegroup(self, cache):
        arr = Array.model_validate(
            {"items": "simplegroup/param", "description": "test"},
            context={"cache": cache},
        )
        assert arr.items is cache["simplegroup/param"]

    def test_oneof_resolves_to_array_oneof(self, cache):
        arr = Array.model_validate(
            {
                "items": {
                    "oneOf": [
                        "simplegroup/success",
                        "simplegroup/include",
                    ],
                },
                "description": "test",
            },
            context={"cache": cache},
        )
        assert isinstance(arr.items, ArrayOneOf)
        assert len(arr.items.one_of) == 2
        assert arr.items.one_of[0] is cache["simplegroup/success"]
        assert arr.items.one_of[1] is cache["simplegroup/include"]

    def test_rejects_group_ref_in_items(self, cache):
        with pytest.raises(ValidationError):
            Array.model_validate(
                {"items": "group/meta", "description": "test"},
                context={"cache": cache},
            )

    def test_is_frozen(self, cache):
        arr = cache["array/params"]
        with pytest.raises(ValidationError):
            arr.description = "modified"  # type: ignore[misc]


# --- Group tests ---


class TestGroup:
    def test_fields_only(self, cache):
        grp = Group.model_validate(
            {
                "description": "test",
                "fields": {"required": {"name": "atom/str"}},
            },
            context={"cache": cache},
        )
        assert grp.fields is not None
        assert grp.containers is None

    def test_containers_only(self, cache):
        grp = Group.model_validate(
            {
                "description": "test",
                "containers": {
                    "required": {"params": "array/params"},
                },
            },
            context={"cache": cache},
        )
        assert grp.fields is None
        assert grp.containers is not None

    def test_both_fields_and_containers(self, cache):
        grp = cache["group/dispatch"]
        assert grp.fields is not None
        assert grp.containers is not None

    def test_rejects_neither_fields_nor_containers(self, cache):
        with pytest.raises(ValidationError):
            Group.model_validate(
                {"description": "test"},
                context={"cache": cache},
            )

    def test_containers_accept_array(self, cache):
        grp = Group.model_validate(
            {
                "description": "test",
                "containers": {
                    "required": {"params": "array/params"},
                },
            },
            context={"cache": cache},
        )
        assert grp.containers is not None
        assert grp.containers.required is not None
        assert grp.containers.required["params"] is cache["array/params"]

    def test_containers_accept_tuple(self, cache):
        grp = Group.model_validate(
            {
                "description": "test",
                "containers": {
                    "optional": {"batch": "tuple/batch"},
                },
            },
            context={"cache": cache},
        )
        assert grp.containers is not None
        assert grp.containers.optional is not None
        assert grp.containers.optional["batch"] is cache["tuple/batch"]

    def test_containers_accept_simplearray(self, cache):
        grp = Group.model_validate(
            {
                "description": "test",
                "containers": {
                    "optional": {"strings": "simplearray/strings"},
                },
            },
            context={"cache": cache},
        )
        assert grp.containers is not None
        assert grp.containers.optional["strings"] is cache["simplearray/strings"]

    def test_containers_accept_simplegroup(self, cache):
        grp = Group.model_validate(
            {
                "description": "test",
                "containers": {
                    "required": {"param": "simplegroup/param"},
                },
            },
            context={"cache": cache},
        )
        assert grp.containers is not None
        assert grp.containers.required["param"] is cache["simplegroup/param"]


class TestGroupFieldConditional:
    def test_accepts_tuple_ref(self, cache):
        entry = GroupFieldConditionalEntry.model_validate(
            {
                "ref": "tuple/batch",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["tuple/batch"]

    def test_accepts_field_ref(self, cache):
        entry = GroupFieldConditionalEntry.model_validate(
            {
                "ref": "atom/str",
                "always_when": {"field": "format", "in": ["json", "jsonl"]},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["atom/str"]

    def test_rejects_array_ref(self, cache):
        with pytest.raises(ValidationError):
            GroupFieldConditionalEntry.model_validate(
                {
                    "ref": "array/params",
                    "only_when": {"field": "x", "equals": "y"},
                },
                context={"cache": cache},
            )

    def test_rejects_no_condition(self, cache):
        with pytest.raises(ValidationError):
            GroupFieldConditionalEntry.model_validate(
                {"ref": "atom/str"},
                context={"cache": cache},
            )


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
        """Group containers don't accept groups (would be circular)."""
        with pytest.raises(ValidationError):
            GroupContainerConditionalEntry.model_validate(
                {
                    "ref": "group/meta",
                    "only_when": {"field": "x", "equals": "y"},
                },
                context={"cache": cache},
            )


class TestGroupFields:
    def test_all_zones(self, cache):
        gf = GroupFields.model_validate(
            {
                "required": {"name": "atom/str"},
                "optional": {"count": "atom/int"},
                "conditional": {
                    "batch": {
                        "ref": "tuple/batch",
                        "only_when": {"field": "mode", "equals": "batch"},
                    },
                },
            },
            context={"cache": cache},
        )
        assert gf.required is not None
        assert gf.optional is not None
        assert gf.conditional is not None


class TestGroupContainers:
    def test_required_and_optional(self, cache):
        gc = GroupContainers.model_validate(
            {
                "required": {"items": "simplegroup/param"},
                "optional": {"params": "array/params"},
            },
            context={"cache": cache},
        )
        assert gc.required is not None
        assert gc.optional is not None


# --- Superarray tests ---


class TestSuperarray:
    def test_string_ref_to_group(self, cache):
        sup = Superarray.model_validate(
            {"items": "group/meta", "description": "test"},
            context={"cache": cache},
        )
        assert sup.items is cache["group/meta"]

    def test_string_ref_to_simplegroup(self, cache):
        sup = Superarray.model_validate(
            {"items": "simplegroup/param", "description": "test"},
            context={"cache": cache},
        )
        assert sup.items is cache["simplegroup/param"]

    def test_oneof_resolves_to_superarray_oneof(self, cache):
        sup = Superarray.model_validate(
            {
                "items": {
                    "oneOf": ["group/meta", "simplegroup/include"],
                },
                "description": "test",
            },
            context={"cache": cache},
        )
        assert isinstance(sup.items, SuperarrayOneOf)
        assert len(sup.items.one_of) == 2
        assert sup.items.one_of[0] is cache["group/meta"]
        assert sup.items.one_of[1] is cache["simplegroup/include"]

    def test_rejects_array_ref_in_items(self, cache):
        with pytest.raises(ValidationError):
            Superarray.model_validate(
                {"items": "array/params", "description": "test"},
                context={"cache": cache},
            )


# --- Section tests ---


class TestSection:
    def test_components_accept_group(self, cache):
        sec = Section.model_validate(
            {
                "description": "test",
                "components": {"meta": "group/meta"},
            },
            context={"cache": cache},
        )
        assert sec.components["meta"] is cache["group/meta"]

    def test_components_accept_array(self, cache):
        sec = Section.model_validate(
            {
                "description": "test",
                "components": {"criteria": "array/criteria"},
            },
            context={"cache": cache},
        )
        assert sec.components["criteria"] is cache["array/criteria"]

    def test_components_accept_superarray(self, cache):
        sec = Section.model_validate(
            {
                "description": "test",
                "components": {"examples": "superarray/examples"},
            },
            context={"cache": cache},
        )
        assert sec.components["examples"] is cache["superarray/examples"]

    def test_rejects_simplegroup_in_components(self, cache):
        with pytest.raises(ValidationError):
            Section.model_validate(
                {
                    "description": "test",
                    "components": {"bad": "simplegroup/param"},
                },
                context={"cache": cache},
            )

    def test_rejects_field_in_components(self, cache):
        with pytest.raises(ValidationError):
            Section.model_validate(
                {
                    "description": "test",
                    "components": {"bad": "atom/str"},
                },
                context={"cache": cache},
            )


# --- Shallowsection tests ---


class TestShallowsection:
    def test_fields_and_containers(self, cache):
        shallow = cache["shallowsection/dispatcher"]
        assert shallow.required is not None
        assert shallow.optional is not None
        assert shallow.conditional is not None
        assert shallow.containers is not None

    def test_fields_only(self, cache):
        ss = Shallowsection.model_validate(
            {
                "description": "test",
                "required": {"name": "atom/str"},
            },
            context={"cache": cache},
        )
        assert ss.required is not None
        assert ss.containers is None

    def test_max_two_containers(self, cache):
        ss = Shallowsection.model_validate(
            {
                "description": "test",
                "required": {"name": "atom/str"},
                "containers": {
                    "required": {"a": "array/params"},
                    "optional": {"b": "simplearray/strings"},
                },
            },
            context={"cache": cache},
        )
        assert ss.containers is not None

    def test_rejects_three_containers(self, cache):
        with pytest.raises(ValidationError):
            Shallowsection.model_validate(
                {
                    "description": "test",
                    "required": {"name": "atom/str"},
                    "containers": {
                        "required": {
                            "a": "array/params",
                            "b": "array/criteria",
                        },
                        "optional": {"c": "simplearray/strings"},
                    },
                },
                context={"cache": cache},
            )


class TestShallowFieldConditional:
    def test_accepts_tuple_ref(self, cache):
        entry = ShallowFieldConditionalEntry.model_validate(
            {
                "ref": "tuple/batch",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["tuple/batch"]

    def test_accepts_field_ref(self, cache):
        entry = ShallowFieldConditionalEntry.model_validate(
            {
                "ref": "enum/mode",
                "not_when": {"field": "x", "equals": "y"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["enum/mode"]

    def test_rejects_array_ref(self, cache):
        with pytest.raises(ValidationError):
            ShallowFieldConditionalEntry.model_validate(
                {
                    "ref": "array/params",
                    "only_when": {"field": "x", "equals": "y"},
                },
                context={"cache": cache},
            )


# --- Schema tests ---


class TestSchema:
    def test_sections_schema(self, cache):
        schema = Schema.model_validate(
            {
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

    def test_accepts_both_sections_and_shallowsections(self, cache):
        schema = Schema.model_validate(
            {
                "version": 1,
                "description": "test",
                "sections": {"indirect": "section/indirect"},
                "shallowsections": {
                    "dispatcher": "shallowsection/dispatcher",
                },
            },
            context={"cache": cache},
        )
        assert schema.sections is not None
        assert schema.shallowsections is not None

    def test_rejects_neither_sections_nor_shallowsections(self, cache):
        with pytest.raises(ValidationError):
            Schema.model_validate(
                {
                    "version": 1,
                    "description": "test",
                },
                context={"cache": cache},
            )

    def test_nullable_field(self, cache):
        schema = Schema.model_validate(
            {
                "version": 1,
                "description": "test",
                "required": ["dispatcher"],
                "nullable": ["optional_section"],
                "shallowsections": {
                    "dispatcher": "shallowsection/dispatcher",
                },
            },
            context={"cache": cache},
        )
        assert schema.nullable == ("optional_section",)

    def test_is_frozen(self, cache):
        schema = Schema.model_validate(
            {
                "version": 3,
                "description": "test",
                "sections": {"indirect": "section/indirect"},
            },
            context={"cache": cache},
        )
        with pytest.raises(ValidationError):
            schema.version = 4  # type: ignore[misc]
