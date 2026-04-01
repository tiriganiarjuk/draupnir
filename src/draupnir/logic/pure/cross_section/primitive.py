"""Cross-section conditional path parsing — single-expression decomposers.

CC=1. Cross-section when-conditions reference fields in other sections
using dotted paths like ".task.processing.output_file_format". These
primitives decompose the path into navigable segments for building
nested JSON Schema if/then/else structures.
"""


def strip_cross_section_marker(field_path: str) -> str:
    """Remove the leading dot that marks a path as cross-section.

    Cross-section paths start with "." to distinguish them from
    same-section field names. The dot is a marker, not a path segment.
    """
    return field_path.lstrip(".")


def split_dotted_path(path: str) -> tuple[tuple[str, ...], str]:
    """Separate parent navigation segments from the leaf field name.

    The parent segments become nested "properties" wrappers in JSON Schema.
    The leaf becomes the "required" or constraint target.
    """
    segments = tuple(path.split("."))
    return segments[:-1], segments[-1]


def parse_cross_section_path(field_path: str) -> tuple[tuple[str, ...], str]:
    """Compose strip + split: '.task.processing.format' -> (('task','processing'), 'format')."""
    return split_dotted_path(strip_cross_section_marker(field_path))
