"""Stabilize field names by stripping pipeline stage suffixes.

Pure: string in, string out. No IO, no side effects.

Stage suffixes exist in YAML filenames and (before Phase 5 migration)
in name: fields. The JSON field name must be the STABLE version without
the suffix. The filename carries the variant, not the name field.
"""

STAGE_SUFFIXES = ("_resolved", "_reduced", "_merged")


def resolve_hybrid_name(raw_name: str) -> str | None:
    """Resolve compound transformation names to their stable form.

    Hybrid names arise from merging two pipeline branches where
    each branch carried its own stage suffix. Order varies by
    which branch resolved first.
    """
    match raw_name:
        case (
            "success_failure_resolved_guardrails_reduced"
            | "success_failure_reduced_guardrails_resolved"
        ):
            return "criteria"
        case (
            "examples_reduced_instructions_resolved"
            | "examples_resolved_instructions_reduced"
        ):
            return "execution"
        case _:
            return None


def stabilize_name(raw_name: str) -> str:
    """Strip pipeline stage suffix from a name.

    Hybrid names (compound transformations) use match/case.
    Simple variants use suffix stripping.
    Returns the name unchanged if no known suffix is found.
    """
    hybrid = resolve_hybrid_name(raw_name)
    if hybrid is not None:
        return hybrid
    for suffix in STAGE_SUFFIXES:
        if raw_name.endswith(suffix):
            return raw_name[: -len(suffix)]
    return raw_name
