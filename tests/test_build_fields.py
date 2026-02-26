"""Tests for build_fields.py — field/simple container → JSON Schema conversion."""

import pytest

from draupnir.functions.pure.build_fields import (
    build_atom,
    build_conditional_entry,
    build_enum,
    build_field,
    build_simplearray,
    build_simplegroup,
    build_tuple,
    build_union,
)
from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.fields import Atom, Element
from draupnir.structures.fields import Enum as VerdandiEnum
from draupnir.structures.fields import Pattern, Union_
from draupnir.structures.schema_output import (
    SchemaArray,
    SchemaCondition,
    SchemaConditional,
    SchemaField,
    SchemaObject,
    SchemaOneOfField,
    SchemaTupleArray,
)
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    SimplegroupConditionalEntry,
    Tuple_,
)


# --- Fixtures: synthetic Verdandi models ---


@pytest.fixture()
def pattern_kebab():
    return Pattern(regex="^[a-z][a-z0-9-]*$", description="kebab-case string")


@pytest.fixture()
def atom_string(pattern_kebab):
    return Atom(type="string", pattern=pattern_kebab, description="a kebab string")


@pytest.fixture()
def atom_integer():
    return Atom(type="integer", description="an integer value")


@pytest.fixture()
def atom_boolean():
    return Atom(type="boolean", description="a boolean flag")


@pytest.fixture()
def enum_color():
    return VerdandiEnum(values=("red", "green", "blue"), description="color choice")


@pytest.fixture()
def element_email(atom_string):
    return Element(inherits=atom_string, format="email", description="email address")


@pytest.fixture()
def union_str_int(atom_string, atom_integer):
    return Union_(union=(atom_string, atom_integer), description="string or integer")


# --- Test build_atom ---


class TestBuildAtom:
    def test_with_pattern(self, atom_string):
        result = build_atom(atom_string)
        assert isinstance(result, SchemaField)
        assert result.type == "string"
        assert result.pattern == "^[a-z][a-z0-9-]*$"
        assert result.description == "a kebab string"

    def test_without_pattern(self, atom_integer):
        result = build_atom(atom_integer)
        assert result.type == "integer"
        assert result.pattern is None
        assert result.description == "an integer value"


# --- Test build_enum ---


class TestBuildEnum:
    def test_enum_values(self, enum_color):
        result = build_enum(enum_color)
        assert isinstance(result, SchemaField)
        assert result.type == "string"
        assert result.enum == ("red", "green", "blue")
        assert result.description == "color choice"


# --- Test build_element ---


class TestBuildElement:
    def test_inherits_atom_adds_format(self, element_email):
        result = build_field(element_email)
        assert isinstance(result, SchemaField)
        assert result.type == "string"
        assert result.pattern == "^[a-z][a-z0-9-]*$"
        assert result.format == "email"
        assert result.description == "email address"

    def test_inherits_enum(self, enum_color):
        elem = Element(inherits=enum_color, format="uri", description="colored uri")
        result = build_field(elem)
        assert result.type == "string"
        assert result.enum == ("red", "green", "blue")
        assert result.format == "uri"


# --- Test build_union ---


class TestBuildUnion:
    def test_produces_oneof(self, union_str_int):
        result = build_union(union_str_int)
        assert isinstance(result, SchemaOneOfField)
        assert len(result.one_of) == 2
        assert result.one_of[0].type == "string"
        assert result.one_of[1].type == "integer"
        assert result.description == "string or integer"


# --- Test build_field dispatch ---


class TestBuildField:
    def test_pattern(self, pattern_kebab):
        result = build_field(pattern_kebab)
        assert isinstance(result, SchemaField)
        assert result.type == "string"
        assert result.pattern == "^[a-z][a-z0-9-]*$"

    def test_atom(self, atom_string):
        result = build_field(atom_string)
        assert isinstance(result, SchemaField)

    def test_enum(self, enum_color):
        result = build_field(enum_color)
        assert isinstance(result, SchemaField)
        assert result.enum is not None

    def test_element(self, element_email):
        result = build_field(element_email)
        assert isinstance(result, SchemaField)
        assert result.format == "email"

    def test_union(self, union_str_int):
        result = build_field(union_str_int)
        assert isinstance(result, SchemaOneOfField)


# --- Test build_tuple ---


class TestBuildTuple:
    def test_two_items(self, atom_string, atom_integer):
        tup = Tuple_(items=(atom_string, atom_integer), description="key-value pair")
        result = build_tuple(tup)
        assert isinstance(result, SchemaTupleArray)
        assert len(result.prefix_items) == 2
        assert result.prefix_items[0].type == "string"
        assert result.prefix_items[1].type == "integer"
        assert result.min_items == 2
        assert result.max_items == 2
        assert result.description == "key-value pair"


# --- Test build_simplearray ---


class TestBuildSimplearray:
    def test_atom_items(self, atom_string):
        sarr = Simplearray(items=atom_string, description="list of strings")
        result = build_simplearray(sarr)
        assert isinstance(result, SchemaArray)
        assert isinstance(result.items, SchemaField)
        assert result.items.type == "string"
        assert result.description == "list of strings"

    def test_union_items(self, union_str_int):
        sarr = Simplearray(items=union_str_int, description="mixed list")
        result = build_simplearray(sarr)
        assert isinstance(result, SchemaArray)
        assert isinstance(result.items, SchemaOneOfField)


# --- Test build_simplegroup ---


class TestBuildSimplegroup:
    def test_required_only(self, atom_string, atom_integer):
        grp = Simplegroup(
            required={"name": atom_string, "count": atom_integer},
            description="simple group",
        )
        result = build_simplegroup(grp)
        assert isinstance(result, SchemaObject)
        assert "name" in result.properties
        assert "count" in result.properties
        assert result.required == ("name", "count")
        assert result.additional_properties is False

    def test_optional_only(self, atom_boolean):
        grp = Simplegroup(
            optional={"flag": atom_boolean},
            description="optional group",
        )
        result = build_simplegroup(grp)
        assert "flag" in result.properties
        assert result.required is None

    def test_mixed_zones(self, atom_string, atom_boolean):
        grp = Simplegroup(
            required={"name": atom_string},
            optional={"flag": atom_boolean},
            description="mixed group",
        )
        result = build_simplegroup(grp)
        assert result.required == ("name",)
        assert "name" in result.properties
        assert "flag" in result.properties

    def test_no_conditionals_means_no_allof(self, atom_string):
        grp = Simplegroup(
            required={"name": atom_string},
            description="no conditionals",
        )
        result = build_simplegroup(grp)
        assert result.all_of is None


# --- Test build_conditional_entry ---


class TestBuildConditionalEntry:
    def test_only_when_equals(self):
        when = ConditionalWhen(field="type", equals="advanced")
        result = build_conditional_entry("extra", when, None, None)
        assert isinstance(result, SchemaConditional)
        assert result.if_ is not None
        assert result.then_ is not None
        assert result.else_ is not None
        assert result.then_.required == ("extra",)

    def test_always_when_no_else(self):
        when = ConditionalWhen(field="mode", equals="debug")
        result = build_conditional_entry("verbose", None, when, None)
        assert result.else_ is None
        assert result.then_.required == ("verbose",)

    def test_not_when_forbids(self):
        when = ConditionalWhen(field="mode", equals="production")
        result = build_conditional_entry("debug_info", None, None, when)
        assert result.else_ is None
        assert isinstance(result.then_, SchemaCondition)

    def test_in_constraint(self):
        when = ConditionalWhen(field="env", in_=("dev", "staging"))
        result = build_conditional_entry("debug", when, None, None)
        assert result.if_ is not None

    def test_raises_when_none(self):
        with pytest.raises(ValueError, match="exactly one"):
            build_conditional_entry("field", None, None, None)


# --- Test build_simplegroup with conditionals ---


class TestBuildSimplegroupConditional:
    def test_conditional_produces_allof(self, atom_string, atom_boolean):
        when = ConditionalWhen(field="type", equals="advanced")
        entry = SimplegroupConditionalEntry(
            ref=atom_boolean, only_when=when,
        )
        grp = Simplegroup(
            required={"type": atom_string},
            conditional={"extra": entry},
            description="conditional group",
        )
        result = build_simplegroup(grp)
        assert result.all_of is not None
        assert len(result.all_of) == 1
        assert "extra" in result.properties
