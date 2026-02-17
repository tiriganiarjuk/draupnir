"""Tests for draupnir.functions.pure.stabilizers — name stabilization."""

from draupnir.functions.pure.stabilizers import stabilize_name


class TestStabilizeName:
    def test_strip_resolved(self) -> None:
        assert stabilize_name("security_resolved") == "security"

    def test_strip_reduced(self) -> None:
        assert stabilize_name("guardrails_reduced") == "guardrails"

    def test_strip_merged(self) -> None:
        assert stabilize_name("criteria_merged") == "criteria"

    def test_no_suffix_unchanged(self) -> None:
        assert stabilize_name("context_path") == "context_path"

    def test_empty_string(self) -> None:
        assert stabilize_name("") == ""

    def test_compound_name_with_suffix(self) -> None:
        assert stabilize_name("security_paths_resolved") == "security_paths"

    def test_suffix_only_at_end(self) -> None:
        """'resolved_context' should NOT be stripped (suffix not at end)."""
        assert stabilize_name("resolved_context") == "resolved_context"

    def test_first_matching_suffix_wins(self) -> None:
        """Edge case: name ending with multiple suffix-like patterns."""
        assert stabilize_name("foo_reduced_resolved") == "foo_reduced"

    def test_hybrid_sf_resolved_guardrails_reduced(self) -> None:
        result = stabilize_name("success_failure_resolved_guardrails_reduced")
        assert result == "criteria"

    def test_hybrid_sf_reduced_guardrails_resolved(self) -> None:
        result = stabilize_name("success_failure_reduced_guardrails_resolved")
        assert result == "criteria"

    def test_hybrid_examples_reduced_instructions_resolved(self) -> None:
        result = stabilize_name("examples_reduced_instructions_resolved")
        assert result == "execution"

    def test_hybrid_examples_resolved_instructions_reduced(self) -> None:
        result = stabilize_name("examples_resolved_instructions_reduced")
        assert result == "execution"
