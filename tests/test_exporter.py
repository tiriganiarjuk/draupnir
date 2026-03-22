"""Tests for exporter.py — tree walk, $defs detection, SchemaDocument assembly."""

import pytest
from pydantic import BaseModel

from draupnir.functions.impure.exporter import (
    export_all_schemas,
    export_schema,
)
from draupnir.functions.pure.tree_walk import (
    count_refs,
    iter_child_models,
    reverse_cache_index,
    shared_keys,
)
from draupnir.structures.complex_containers import (
    Array,
    Group,
    GroupContainers,
    GroupFields,
)
from draupnir.structures.fields import Atom, Pattern
from draupnir.structures.schema_output import SchemaDocument, SchemaObject
from draupnir.structures.simple_containers import Simplegroup, VerdandiField
from draupnir.structures.top_level import (
    Schema,
    SchemaShallowsections,
    Shallowsection,
    ShallowsectionFields,
)


# --- Fixtures ---


@pytest.fixture()
def atom_string():
    pattern = Pattern(title="Lowercase", regex="^[a-z]+$", description="lowercase")
    return Atom(title="String", type="string", pattern=pattern, description="string")


@pytest.fixture()
def atom_integer():
    return Atom(title="Integer", type="integer", description="integer")


@pytest.fixture()
def field_string(atom_string):
    return VerdandiField(
        title="Name", type=atom_string, description="a name field",
    )


@pytest.fixture()
def field_integer(atom_integer):
    return VerdandiField(
        title="Count", type=atom_integer, description="a count field",
    )


@pytest.fixture()
def shared_simplegroup(field_string, field_integer):
    """A simplegroup used by multiple parents (shared node)."""
    return Simplegroup(
        title="SharedEntry",
        required={"name": field_string, "count": field_integer},
        description="shared entry",
    )


@pytest.fixture()
def array_using_shared(shared_simplegroup):
    return Array(title="ListA", items=shared_simplegroup, description="list A")


@pytest.fixture()
def group_using_shared(shared_simplegroup, field_string):
    return Group(
        title="GroupB",
        fields=GroupFields(required={"label": field_string}),
        containers=GroupContainers(required={"items": shared_simplegroup}),
        description="group B",
    )


@pytest.fixture()
def cache_with_sharing(
    atom_string, atom_integer, field_string, field_integer,
    shared_simplegroup, array_using_shared, group_using_shared,
):
    """Cache where shared_simplegroup appears in 2 parents."""
    return {
        "atom/string": atom_string,
        "atom/integer": atom_integer,
        "field/name": field_string,
        "field/count": field_integer,
        "simplegroup/entry": shared_simplegroup,
        "array/list_a": array_using_shared,
        "group/group_b": group_using_shared,
    }


# --- Test reverse_cache_index ---


class TestReverseCacheIndex:
    def test_maps_id_to_key(self, atom_string, atom_integer):
        cache = {"atom/string": atom_string, "atom/integer": atom_integer}
        reverse = reverse_cache_index(cache)
        assert reverse[id(atom_string)] == "atom/string"
        assert reverse[id(atom_integer)] == "atom/integer"


# --- Test iter_child_models ---


class TestIterChildModels:
    def test_atom_yields_pattern(self, atom_string):
        children = list(iter_child_models(atom_string))
        assert len(children) == 1
        assert isinstance(children[0], Pattern)

    def test_simplegroup_yields_dict_values(self, shared_simplegroup):
        children = list(iter_child_models(shared_simplegroup))
        assert any(isinstance(child, VerdandiField) for child in children)

    def test_array_yields_items(self, array_using_shared):
        children = list(iter_child_models(array_using_shared))
        assert any(isinstance(child, Simplegroup) for child in children)


# --- Test count_refs ---


class TestCountRefs:
    def test_shared_node_counted_twice(self, cache_with_sharing):
        reverse = reverse_cache_index(cache_with_sharing)
        root_group = cache_with_sharing["group/group_b"]
        root_array = cache_with_sharing["array/list_a"]

        counts_group = count_refs(root_group, reverse)
        counts_array = count_refs(root_array, reverse)

        assert counts_group.get("simplegroup/entry", 0) >= 1
        assert counts_array.get("simplegroup/entry", 0) >= 1


# --- Test shared_keys ---


class TestSharedKeys:
    def test_filters_by_count(self):
        counts = {"a": 1, "b": 2, "c": 3, "d": 1}
        result = shared_keys(counts)
        assert result == frozenset({"b", "c"})

    def test_empty_counts(self):
        assert shared_keys({}) == frozenset()


# --- Test export_schema ---


class TestExportSchema:
    def test_produces_schema_document(self, field_string, field_integer):
        shallow = Shallowsection(
            title="Identity",
            fields=ShallowsectionFields(
                required={"name": field_string},
                optional={"count": field_integer},
            ),
            description="identity",
        )
        schema = Schema(
            title="Test",
            version=1,
            description="test schema",
            shallowsections=SchemaShallowsections(
                required={"identity": shallow},
            ),
        )
        cache: dict[str, BaseModel] = {
            "field/name": field_string,
            "field/count": field_integer,
            "shallowsection/identity": shallow,
            "schema/test": schema,
        }
        result = export_schema(schema, "schema/test", cache)
        assert isinstance(result, SchemaDocument)
        assert result.schema_id == "test.schema.json"
        assert result.title == "Test"
        assert "identity" in result.properties
        assert result.required == ("identity",)

    def test_optional_section_not_in_required(self, field_string):
        shallow = Shallowsection(
            title="Section",
            fields=ShallowsectionFields(
                required={"name": field_string},
            ),
            description="section",
        )
        schema = Schema(
            title="OptionalTest",
            version=1,
            description="optional test",
            shallowsections=SchemaShallowsections(
                optional={"section": shallow},
            ),
        )
        cache: dict[str, BaseModel] = {
            "field/name": field_string,
            "shallowsection/section": shallow,
            "schema/optional": schema,
        }
        result = export_schema(schema, "schema/optional", cache)
        assert "section" in result.properties
        assert result.required is None
        assert isinstance(result.properties["section"], SchemaObject)


# --- Test export_all_schemas ---


class TestExportAllSchemas:
    def test_exports_only_schemas(self, field_string, field_integer):
        shallow = Shallowsection(
            title="Identity",
            fields=ShallowsectionFields(
                required={"name": field_string},
            ),
            description="identity",
        )
        schema = Schema(
            title="Test",
            version=1,
            description="test",
            shallowsections=SchemaShallowsections(
                required={"identity": shallow},
            ),
        )
        cache: dict[str, BaseModel] = {
            "field/name": field_string,
            "field/count": field_integer,
            "shallowsection/identity": shallow,
            "schema/test": schema,
        }
        results = export_all_schemas(cache)
        assert len(results) == 1
        assert "schema/test" in results
        assert isinstance(results["schema/test"], SchemaDocument)
