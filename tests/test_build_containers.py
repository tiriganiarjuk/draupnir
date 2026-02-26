"""Tests for build_containers.py — container → JSON Schema + $defs/$ref."""

import pytest
from pydantic import BaseModel

from draupnir.functions.pure.build_containers import (
    build_array,
    build_group,
    build_model,
    build_or_ref,
    build_section,
    build_shallowsection,
    build_superarray,
    defs_key,
)
from draupnir.structures.complex_containers import (
    Array,
    ArrayOneOf,
    Group,
    GroupContainers,
    GroupFields,
    Superarray,
    SuperarrayOneOf,
)
from draupnir.structures.fields import Atom, Pattern
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaObject,
    SchemaRef,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
)
from draupnir.structures.top_level import (
    Section,
    Shallowsection,
    ShallowContainers,
)


# --- Fixtures ---


@pytest.fixture()
def pattern_kebab():
    return Pattern(regex="^[a-z]+$", description="lowercase")


@pytest.fixture()
def atom_string(pattern_kebab):
    return Atom(type="string", pattern=pattern_kebab, description="string")


@pytest.fixture()
def atom_integer():
    return Atom(type="integer", description="integer")


@pytest.fixture()
def atom_boolean():
    return Atom(type="boolean", description="boolean")


@pytest.fixture()
def simplegroup_entry(atom_string, atom_integer):
    return Simplegroup(
        required={"name": atom_string, "count": atom_integer},
        description="entry",
    )


@pytest.fixture()
def simplegroup_alt(atom_boolean):
    return Simplegroup(
        required={"flag": atom_boolean},
        description="alt entry",
    )


@pytest.fixture()
def array_of_entries(simplegroup_entry):
    return Array(items=simplegroup_entry, description="entry list")


@pytest.fixture()
def array_oneof(simplegroup_entry, simplegroup_alt):
    return Array(
        items=ArrayOneOf(one_of=(simplegroup_entry, simplegroup_alt)),
        description="polymorphic list",
    )


@pytest.fixture()
def group_with_fields(atom_string, atom_integer):
    return Group(
        fields=GroupFields(
            required={"name": atom_string},
            optional={"count": atom_integer},
        ),
        description="field group",
    )


@pytest.fixture()
def group_with_containers(simplegroup_entry, array_of_entries):
    return Group(
        containers=GroupContainers(
            required={"entries": array_of_entries},
            optional={"extra": simplegroup_entry},
        ),
        description="container group",
    )


@pytest.fixture()
def superarray_simple(simplegroup_entry):
    return Superarray(items=simplegroup_entry, description="super list")


@pytest.fixture()
def section_model(group_with_containers, array_of_entries):
    return Section(
        components={"data": group_with_containers, "items": array_of_entries},
        description="a section",
    )


@pytest.fixture()
def shallowsection_model(atom_string, atom_integer, array_of_entries):
    return Shallowsection(
        required={"name": atom_string},
        optional={"count": atom_integer},
        containers=ShallowContainers(required={"items": array_of_entries}),
        description="a shallowsection",
    )


def empty_defs_args():
    """Return empty reverse/shared/defs for non-shared builds."""
    return {}, frozenset(), {}


# --- Test defs_key ---


class TestDefsKey:
    def test_converts_slash(self):
        assert defs_key("simplegroup/foo") == "simplegroup__foo"

    def test_nested_path(self):
        assert defs_key("array/bar_baz") == "array__bar_baz"


# --- Test build_array ---


class TestBuildArray:
    def test_single_items(self, array_of_entries):
        reverse, shared, defs = empty_defs_args()
        result = build_array(array_of_entries, reverse, shared, defs)
        assert isinstance(result, SchemaArray)
        assert isinstance(result.items, SchemaObject)
        assert result.description == "entry list"

    def test_oneof_items(self, array_oneof):
        reverse, shared, defs = empty_defs_args()
        result = build_array(array_oneof, reverse, shared, defs)
        assert isinstance(result, SchemaArray)
        assert hasattr(result.items, "one_of")


# --- Test build_superarray ---


class TestBuildSuperarray:
    def test_single_items(self, superarray_simple):
        reverse, shared, defs = empty_defs_args()
        result = build_superarray(superarray_simple, reverse, shared, defs)
        assert isinstance(result, SchemaArray)
        assert isinstance(result.items, SchemaObject)

    def test_oneof_items(self, simplegroup_entry, simplegroup_alt):
        sarr = Superarray(
            items=SuperarrayOneOf(one_of=(simplegroup_entry, simplegroup_alt)),
            description="poly super",
        )
        reverse, shared, defs = empty_defs_args()
        result = build_superarray(sarr, reverse, shared, defs)
        assert isinstance(result, SchemaArray)
        assert hasattr(result.items, "one_of")


# --- Test build_group ---


class TestBuildGroup:
    def test_fields_only(self, group_with_fields):
        reverse, shared, defs = empty_defs_args()
        result = build_group(group_with_fields, reverse, shared, defs)
        assert isinstance(result, SchemaObject)
        assert "name" in result.properties
        assert "count" in result.properties
        assert "name" in result.required

    def test_containers_only(self, group_with_containers):
        reverse, shared, defs = empty_defs_args()
        result = build_group(group_with_containers, reverse, shared, defs)
        assert isinstance(result, SchemaObject)
        assert "entries" in result.properties
        assert "extra" in result.properties


# --- Test build_section ---


class TestBuildSection:
    def test_components_as_properties(self, section_model):
        reverse, shared, defs = empty_defs_args()
        result = build_section(section_model, reverse, shared, defs)
        assert isinstance(result, SchemaObject)
        assert "data" in result.properties
        assert "items" in result.properties
        assert set(result.required) == {"data", "items"}


# --- Test build_shallowsection ---


class TestBuildShallowsection:
    def test_fields_and_containers(self, shallowsection_model):
        reverse, shared, defs = empty_defs_args()
        result = build_shallowsection(shallowsection_model, reverse, shared, defs)
        assert isinstance(result, SchemaObject)
        assert "name" in result.properties
        assert "count" in result.properties
        assert "items" in result.properties
        assert "name" in result.required
        assert "items" in result.required


# --- Test build_or_ref with $defs ---


class TestBuildOrRef:
    def test_non_shared_builds_inline(self, simplegroup_entry):
        reverse = {id(simplegroup_entry): "simplegroup/entry"}
        shared: frozenset[str] = frozenset()
        defs: dict[str, BaseModel] = {}
        result = build_or_ref(simplegroup_entry, reverse, shared, defs)
        assert isinstance(result, SchemaObject)
        assert len(defs) == 0

    def test_shared_extracts_to_defs(self, simplegroup_entry):
        reverse = {id(simplegroup_entry): "simplegroup/entry"}
        shared = frozenset({"simplegroup/entry"})
        defs: dict[str, BaseModel] = {}
        result = build_or_ref(simplegroup_entry, reverse, shared, defs)
        assert isinstance(result, SchemaRef)
        assert result.ref == "#/$defs/simplegroup__entry"
        assert "simplegroup__entry" in defs

    def test_shared_second_ref_reuses_def(self, simplegroup_entry):
        reverse = {id(simplegroup_entry): "simplegroup/entry"}
        shared = frozenset({"simplegroup/entry"})
        defs: dict[str, BaseModel] = {}
        first = build_or_ref(simplegroup_entry, reverse, shared, defs)
        second = build_or_ref(simplegroup_entry, reverse, shared, defs)
        assert isinstance(first, SchemaRef)
        assert isinstance(second, SchemaRef)
        assert first.ref == second.ref
        assert len(defs) == 1


# --- Test build_model dispatch ---


class TestBuildModel:
    def test_dispatches_simplegroup(self, simplegroup_entry):
        reverse, shared, defs = empty_defs_args()
        result = build_model(simplegroup_entry, reverse, shared, defs)
        assert isinstance(result, SchemaObject)

    def test_dispatches_array(self, array_of_entries):
        reverse, shared, defs = empty_defs_args()
        result = build_model(array_of_entries, reverse, shared, defs)
        assert isinstance(result, SchemaArray)

    def test_dispatches_atom(self, atom_string):
        from draupnir.structures.schema_output import SchemaField

        reverse, shared, defs = empty_defs_args()
        result = build_model(atom_string, reverse, shared, defs)
        assert isinstance(result, SchemaField)
