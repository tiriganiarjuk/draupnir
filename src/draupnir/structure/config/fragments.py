"""Fragment registry — maps output names to Verdandi cache keys.

Each entry is (output_schema_name, cache_key). Used by the pipeline
to export standalone include-fragment schemas.
"""

from enum import Enum


class Fragment(Enum):
    """Known include-fragment schemas with their cache keys."""

    include_success_criteria = "array/success_criteria_reduced"
    include_failure_criteria = "array/failure_criteria_reduced"
    include_execution_instructions = "array/execution_instructions_reduced"
    include_example_entries = "array/example_entries_reduced"
    include_example_group = "group/example_group_reduced"
    include_guardrails_constraints = "simplearray/guardrails_constraints"
    include_guardrails_anti_patterns = "simplearray/guardrails_anti_patterns"
