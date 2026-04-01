"""Cross-section conditional building — single-expression constructors.

CC=1. Path parsing for cross-section conditional predicates. No branching.
"""


def strip_cross_section_marker(field_path: str) -> str:
    """Remove leading dot from cross-section field path."""
    return field_path.lstrip(".")


def split_dotted_path(path: str) -> tuple[tuple[str, ...], str]:
    """Split dotted path into (parent_segments, leaf_name)."""
    segments = tuple(path.split("."))
    return segments[:-1], segments[-1]


def parse_cross_section_path(field_path: str) -> tuple[tuple[str, ...], str]:
    """Parse cross-section path: '.a.b.c' -> (('a', 'b'), 'c')."""
    return split_dotted_path(strip_cross_section_marker(field_path))
