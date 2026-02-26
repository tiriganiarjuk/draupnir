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
)


@pytest.fixture
def cache():
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
    base = {
        "atom/str": atom_str,
        "atom/int": atom_int,
        "enum/mode": enum_mode,
        "pattern/rel": pattern_rel,
        "union/path": union_path,
    }
    # Build tuple and simplearray referencing field types
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
                "field": "indirect.dispatch.dispatch_input_delivery",
                "equals": "file",
            }
        )
        assert "." in cw.field


class TestTuple:
    def test_resolves_items_from_cache(self, cache):
        tup = Tuple_.model_validate(
            {
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
            {"items": ["atom/str"], "description": "test"},
            context={"cache": cache},
        )
        assert tup.constraint is None

    def test_rejects_missing_cache_ref(self, cache):
        with pytest.raises(ValidationError):
            Tuple_.model_validate(
                {"items": ["atom/nonexistent"], "description": "test"},
                context={"cache": cache},
            )


class TestSimplearray:
    def test_resolves_single_item_from_cache(self, cache):
        sa = Simplearray.model_validate(
            {"items": "atom/str", "description": "test"},
            context={"cache": cache},
        )
        assert sa.items is cache["atom/str"]

    def test_accepts_union_ref(self, cache):
        sa = Simplearray.model_validate(
            {"items": "union/path", "description": "test"},
            context={"cache": cache},
        )
        assert sa.items is cache["union/path"]


class TestSimplegroup:
    def test_required_zone_resolves_refs(self, cache):
        sg = Simplegroup.model_validate(
            {
                "description": "test",
                "required": {"name": "atom/str", "count": "atom/int"},
            },
            context={"cache": cache},
        )
        assert sg.required is not None
        assert sg.required["name"] is cache["atom/str"]
        assert sg.required["count"] is cache["atom/int"]

    def test_accepts_simplearray_in_required(self, cache):
        sg = Simplegroup.model_validate(
            {
                "description": "test",
                "required": {
                    "label": "atom/str",
                    "items": "simplearray/strings",
                },
            },
            context={"cache": cache},
        )
        assert sg.required is not None
        assert sg.required["items"] is cache["simplearray/strings"]

    def test_accepts_tuple_in_optional(self, cache):
        sg = Simplegroup.model_validate(
            {
                "description": "test",
                "required": {"name": "atom/str"},
                "optional": {"batch": "tuple/batch"},
            },
            context={"cache": cache},
        )
        assert sg.optional is not None
        assert sg.optional["batch"] is cache["tuple/batch"]

    def test_rejects_all_zones_empty(self, cache):
        with pytest.raises(ValidationError):
            Simplegroup.model_validate(
                {"description": "test"},
                context={"cache": cache},
            )

    def test_optional_only_is_valid(self, cache):
        sg = Simplegroup.model_validate(
            {
                "description": "test",
                "optional": {"name": "atom/str"},
            },
            context={"cache": cache},
        )
        assert sg.required is None
        assert sg.optional is not None


class TestSimplegroupConditional:
    def test_conditional_with_only_when(self, cache):
        entry = SimplegroupConditionalEntry.model_validate(
            {
                "ref": "atom/str",
                "only_when": {"field": "mode", "equals": "batch"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["atom/str"]
        assert entry.only_when is not None
        assert entry.only_when.equals == "batch"

    def test_conditional_with_always_when(self, cache):
        entry = SimplegroupConditionalEntry.model_validate(
            {
                "ref": "enum/mode",
                "always_when": {"field": "format", "in": ["json", "jsonl"]},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["enum/mode"]
        assert entry.always_when is not None
        assert entry.always_when.in_ == ("json", "jsonl")

    def test_rejects_no_condition(self, cache):
        with pytest.raises(ValidationError):
            SimplegroupConditionalEntry.model_validate(
                {"ref": "atom/str"},
                context={"cache": cache},
            )

    def test_rejects_multiple_conditions(self, cache):
        with pytest.raises(ValidationError):
            SimplegroupConditionalEntry.model_validate(
                {
                    "ref": "atom/str",
                    "only_when": {"field": "a", "equals": "x"},
                    "not_when": {"field": "b", "equals": "y"},
                },
                context={"cache": cache},
            )

    def test_simplegroup_with_conditional_zone(self, cache):
        sg = Simplegroup.model_validate(
            {
                "description": "test",
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
            context={"cache": cache},
        )
        assert sg.conditional is not None
        assert sg.conditional["batch_size"].ref is cache["tuple/batch"]

    def test_conditional_accepts_simplearray_ref(self, cache):
        entry = SimplegroupConditionalEntry.model_validate(
            {
                "ref": "simplearray/strings",
                "not_when": {"field": "mode", "equals": "full"},
            },
            context={"cache": cache},
        )
        assert entry.ref is cache["simplearray/strings"]
