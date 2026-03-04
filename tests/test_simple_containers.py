"""Tests for conditionals and simple container models."""

import pytest
from pydantic import ValidationError

from draupnir.structures.conditionals import ConditionalWhen
from draupnir.structures.fields import Atom, Enum, Pattern, Union_
from draupnir.structures.simple_containers import (
    Simplearray,
    Simplegroup,
    SimplegroupConditionalEntry,
    Tuple_,
    VerdandiField,
)


@pytest.fixture
def cache():
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
    field_path = VerdandiField(
        title="FieldPath", type=union_path, description="a path field",
    )
    base = {
        "atom/str": atom_str,
        "atom/int": atom_int,
        "enum/mode": enum_mode,
        "pattern/rel": pattern_rel,
        "union/path": union_path,
        "field/str": field_str,
        "field/int": field_int,
        "field/mode": field_mode,
        "field/path": field_path,
    }
    # Build tuple and simplearray referencing field types
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
    base["tuple/batch"] = tup
    base["simplearray/strings"] = sa
    return base


class TestConditionalWhen:
    def test_equals_single_value(self):
        cw = ConditionalWhen.model_validate(
            {"field": "dispatch_mode", "equals": "batch"}
        )
        assert cw.field == "dispatch_mode"
        assert cw.equals == "batch"
        assert cw.in_ is None

    def test_in_multiple_values(self):
        cw = ConditionalWhen.model_validate(
            {"field": "return_mode", "in": ["status-metrics", "metrics-output"]}
        )
        assert cw.field == "return_mode"
        assert cw.equals is None
        assert cw.in_ == ("status-metrics", "metrics-output")

    def test_equals_boolean(self):
        cw = ConditionalWhen.model_validate(
            {"field": "scratch_needed", "equals": True}
        )
        assert cw.equals is True

    def test_rejects_both_equals_and_in(self):
        with pytest.raises(ValidationError):
            ConditionalWhen.model_validate(
                {"field": "x", "equals": "a", "in": ["b"]}
            )

    def test_rejects_neither_equals_nor_in(self):
        with pytest.raises(ValidationError):
            ConditionalWhen.model_validate({"field": "x"})

    def test_is_frozen(self):
        cw = ConditionalWhen(field="x", equals="a")
        with pytest.raises(ValidationError):
            cw.field = "y"  # type: ignore[misc]

    def test_dotted_field_path(self):
        cw = ConditionalWhen.model_validate(
            {
                "field": ".indirect.dispatch.dispatch_input_delivery",
                "equals": "file",
            }
        )
        assert cw.field.startswith(".")

    def test_exists_true(self):
        cw = ConditionalWhen.model_validate(
            {"field": "enforcement_output_tool", "exists": True}
        )
        assert cw.exists is True
        assert cw.equals is None
        assert cw.in_ is None

    def test_exists_cross_section(self):
        cw = ConditionalWhen.model_validate(
            {"field": ".task.processing.output_file_format", "exists": True}
        )
        assert cw.exists is True
        assert cw.field.startswith(".")

    def test_rejects_exists_false(self):
        with pytest.raises(ValidationError):
            ConditionalWhen.model_validate(
                {"field": "x", "exists": False}
            )

    def test_rejects_exists_with_equals(self):
        with pytest.raises(ValidationError):
            ConditionalWhen.model_validate(
                {"field": "x", "exists": True, "equals": "a"}
            )

    def test_rejects_exists_with_in(self):
        with pytest.raises(ValidationError):
            ConditionalWhen.model_validate(
                {"field": "x", "exists": True, "in": ["a"]}
            )


class TestTuple:
    def test_resolves_items_from_cache(self, cache):
        tup = Tuple_.model_validate(
            {
                "title": "Test",
                "items": ["atom/str", "atom/int"],
                "constraint": "ascending_strict",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert tup.items[0] is cache["atom/str"]
        assert tup.items[1] is cache["atom/int"]
        assert tup.constraint == "ascending_strict"

    def test_optional_constraint(self, cache):
        tup = Tuple_.model_validate(
            {"title": "Test", "items": ["atom/str"], "description": "test"},
            context={"cache": cache},
        )
        assert tup.constraint is None

    def test_rejects_missing_cache_ref(self, cache):
        with pytest.raises(ValidationError):
            Tuple_.model_validate(
                {
                    "title": "Test",
                    "items": ["atom/nonexistent"],
                    "description": "test",
                },
                context={"cache": cache},
            )


class TestSimplearray:
    def test_resolves_single_item_from_cache(self, cache):
        sa = Simplearray.model_validate(
            {"title": "Test", "items": "field/str", "description": "test"},
            context={"cache": cache},
        )
        assert sa.items is cache["field/str"]

    def test_accepts_union_field_ref(self, cache):
        sa = Simplearray.model_validate(
            {"title": "Test", "items": "field/path", "description": "test"},
            context={"cache": cache},
        )
        assert sa.items is cache["field/path"]


class TestSimplegroup:
    def test_required_zone_resolves_refs(self, cache):
        sg = Simplegroup.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {"name": "field/str", "count": "field/int"},
            },
            context={"cache": cache},
        )
        assert sg.required is not None
        assert sg.required["name"] is cache["field/str"]
        assert sg.required["count"] is cache["field/int"]

    def test_accepts_simplearray_in_required(self, cache):
        sg = Simplegroup.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {
                    "label": "field/str",
                    "items": "simplearray/strings",
                },
            },
            context={"cache": cache},
        )
        assert sg.required is not None
        assert sg.required["items"] is cache["simplearray/strings"]

    def test_accepts_simplearray_in_optional(self, cache):
        sg = Simplegroup.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {"name": "field/str"},
                "optional": {"items": "simplearray/strings"},
            },
            context={"cache": cache},
        )
        assert sg.optional is not None
        assert sg.optional["items"] is cache["simplearray/strings"]

    def test_rejects_all_zones_empty(self, cache):
        with pytest.raises(ValidationError):
            Simplegroup.model_validate(
                {"title": "Test", "description": "test"},
                context={"cache": cache},
            )

    def test_optional_only_is_valid(self, cache):
        sg = Simplegroup.model_validate(
            {
                "title": "Test",
                "description": "test",
                "optional": {"name": "field/str"},
            },
            context={"cache": cache},
        )
        assert sg.required is None
        assert sg.optional is not None


class TestSimplegroupConditional:
    def test_conditional_with_only_when(self, cache):
        entry = SimplegroupConditionalEntry.model_validate(
            {
                "ref": "field/str",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["field/str"]
        assert entry.only_when is not None
        assert entry.only_when.equals == "batch"

    def test_conditional_with_always_when(self, cache):
        entry = SimplegroupConditionalEntry.model_validate(
            {
                "ref": "field/mode",
                "always_when": {"field": "format", "in": ["json", "jsonl"]},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["field/mode"]
        assert entry.always_when is not None
        assert entry.always_when.in_ == ("json", "jsonl")

    def test_rejects_no_condition(self, cache):
        with pytest.raises(ValidationError):
            SimplegroupConditionalEntry.model_validate(
                {"ref": "field/str"},
                context={"cache": cache},
            )

    def test_rejects_multiple_conditions(self, cache):
        with pytest.raises(ValidationError):
            SimplegroupConditionalEntry.model_validate(
                {
                    "ref": "field/str",
                    "only_when": {"field": "a", "equals": "x"},
                    "not_when": {"field": "b", "equals": "y"},
                },
                context={"cache": cache},
            )

    def test_simplegroup_with_conditional_zone(self, cache):
        sg = Simplegroup.model_validate(
            {
                "title": "Test",
                "description": "test",
                "required": {"mode": "field/mode"},
                "conditional": {
                    "extra": {
                        "ref": "field/str",
                        "only_when": {
                            "field": "mode",
                            "equals": "batch",
                        },
                    },
                },
            },
            context={"cache": cache},
        )
        assert sg.conditional is not None
        assert sg.conditional["extra"].ref is cache["field/str"]

    def test_conditional_accepts_simplearray_ref(self, cache):
        entry = SimplegroupConditionalEntry.model_validate(
            {
                "ref": "simplearray/strings",
                "not_when": {"field": "mode", "equals": "full"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["simplearray/strings"]
