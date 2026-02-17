"""Stabilize field names by stripping pipeline stage suffixes.

Pure: string in, string out. No IO, no side effects.

Stage suffixes exist in YAML filenames and (before Phase 5 migration)
in name: fields. The JSON field name must be the STABLE version without
the suffix. The filename carries the variant, not the name field.
"""

STAGE_SUFFIXES = ("_resolved", "_reduced", "_merged")


def stabilize_name(raw_name: str) -> str:
    """Strip pipeline stage suffix from a name.

    Returns the name unchanged if no known suffix is found.
    Examples: 'security_resolved' → 'security', 'context_path' → 'context_path'.
    """
    for suffix in STAGE_SUFFIXES:
        if raw_name.endswith(suffix):
            return raw_name[: -len(suffix)]
    return raw_name
