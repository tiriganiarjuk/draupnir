"""Stabilize field names by stripping pipeline stage suffixes.

Pure: string in, string out. No IO, no side effects.

Stage suffixes exist in YAML filenames and (before Phase 5 migration)
in name: fields. The JSON field name must be the STABLE version without
the suffix. The filename carries the variant, not the name field.
"""

STAGE_SUFFIXES = ("_resolved", "_reduced", "_merged")

HYBRID_NAMES: dict[str, str] = {
    "success_failure_resolved_guardrails_reduced": "criteria",
    "success_failure_reduced_guardrails_resolved": "criteria",
    "examples_reduced_instructions_resolved": "execution",
    "examples_resolved_instructions_reduced": "execution",
}


def stabilize_name(raw_name: str) -> str:
    """Strip pipeline stage suffix from a name.

    Hybrid names (compound transformations) use an explicit map.
    Simple variants use suffix stripping.
    Returns the name unchanged if no known suffix is found.
    """
    if raw_name in HYBRID_NAMES:
        return HYBRID_NAMES[raw_name]
    for suffix in STAGE_SUFFIXES:
        if raw_name.endswith(suffix):
            return raw_name[: -len(suffix)]
    return raw_name
