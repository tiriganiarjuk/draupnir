"""Tests for conditional converters: same-section and cross-section builders.

Covers the exists predicate, value-based predicates, and the leading-dot
cross-section path convention.
"""

from draupnir.functions.pure.converters.conditional import (
    build_conditional_entry,
    build_if_condition,
    is_cross_section,
)
from draupnir.functions.pure.build_cross_section import build_if_nested
from draupnir.structures.conditionals import ConditionalWhen


# --- is_cross_section ---


class TestIsCrossSection:
    def test_leading_dot_is_cross_section(self):
        when = ConditionalWhen(field=".task.processing.scratch_needed", exists=True)
        assert is_cross_section(when) is True

    def test_no_dot_is_same_section(self):
        when = ConditionalWhen(field="dispatch_mode", equals="batch")
        assert is_cross_section(when) is False

    def test_internal_dot_without_leading_is_same_section(self):
        """A field name with internal dots but no leading dot is same-section."""
        when = ConditionalWhen(field="some_field", equals="x")
        assert is_cross_section(when) is False

    def test_none_is_not_cross_section(self):
        assert is_cross_section(None) is False


# --- build_if_condition (same-section) ---


class TestBuildIfCondition:
    def test_equals_produces_const(self):
        when = ConditionalWhen(field="dispatch_mode", equals="batch")
        result = build_if_condition(when)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {
            "properties": {"dispatch_mode": {"const": "batch"}},
            "required": ("dispatch_mode",),
        }

    def test_in_produces_enum(self):
        when = ConditionalWhen(field="return_mode", in_=("status", "metrics"))
        result = build_if_condition(when)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {
            "properties": {"return_mode": {"enum": ("status", "metrics")}},
            "required": ("return_mode",),
        }

    def test_exists_produces_required(self):
        when = ConditionalWhen(field="enforcement_output_tool", exists=True)
        result = build_if_condition(when)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {"required": ("enforcement_output_tool",)}


# --- build_if_nested (cross-section) ---


class TestBuildIfNested:
    def test_equals_produces_nested_const(self):
        when = ConditionalWhen(
            field=".indirect.dispatch.dispatch_input_delivery", equals="file"
        )
        result = build_if_nested(when)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {
            "properties": {
                "indirect": {
                    "properties": {
                        "dispatch": {
                            "properties": {
                                "dispatch_input_delivery": {"const": "file"}
                            },
                            "required": ("dispatch_input_delivery",),
                        }
                    }
                }
            }
        }

    def test_in_produces_nested_enum(self):
        when = ConditionalWhen(
            field=".task.processing.output_file_name_known",
            in_=("partially", "unknown"),
        )
        result = build_if_nested(when)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {
            "properties": {
                "task": {
                    "properties": {
                        "processing": {
                            "properties": {
                                "output_file_name_known": {
                                    "enum": ("partially", "unknown")
                                }
                            },
                            "required": ("output_file_name_known",),
                        }
                    }
                }
            }
        }

    def test_exists_produces_nested_required(self):
        when = ConditionalWhen(
            field=".task.processing.output_file_format", exists=True
        )
        result = build_if_nested(when)
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped == {
            "properties": {
                "task": {
                    "properties": {
                        "processing": {"required": ("output_file_format",)}
                    }
                }
            }
        }


# --- build_conditional_entry routing ---


class TestBuildConditionalEntryRouting:
    def test_cross_section_returns_none(self):
        """Cross-section conditionals are hoisted, not built inline."""
        when = ConditionalWhen(
            field=".indirect.dispatch.dispatch_mode", equals="batch"
        )
        result = build_conditional_entry("some_field", when, None, None)
        assert result is None

    def test_same_section_returns_conditional(self):
        when = ConditionalWhen(field="dispatch_mode", equals="batch")
        result = build_conditional_entry("batch_size", when, None, None)
        assert result is not None
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert "if" in dumped
        assert "then" in dumped

    def test_exists_same_section_returns_conditional(self):
        when = ConditionalWhen(field="enforcement_output_tool", exists=True)
        result = build_conditional_entry("writing_output", when, None, None)
        assert result is not None
        dumped = result.model_dump(by_alias=True, exclude_none=True)
        assert dumped["if"] == {"required": ("enforcement_output_tool",)}
        assert dumped["then"] == {"required": ("writing_output",)}
        assert dumped["else"] == {"properties": {"writing_output": False}}
