"""Pipeline drift detection.

CC=4-8 functions.

check_schema_drift: compares freshly compiled schemas against what's on disk.
  Used by --check mode to detect when source YAML changed but schemas weren't
  regenerated. Serializes each compiled schema and does string comparison
  against the file content (rstrip to handle trailing newline differences).
"""

from pathlib import Path

from draupnir.logic.pure.serialize.primitive import schema_filename, serialize_schema
from draupnir.structure.model.schema_output import SchemaDocument


def check_schema_drift(
    schemas: dict[str, SchemaDocument],
    output_dir: Path,
) -> list[str]:
    """Compare compiled schemas against on-disk files. Returns list of drift messages.

    Detects two types of drift: missing files (not yet generated) and content
    differences (source YAML changed but output not regenerated). Serializes
    each schema fresh to compare, ensuring the comparison uses the same
    formatting as write_schema would produce.
    """
    messages: list[str] = []
    for cache_key, document in schemas.items():
        path = output_dir / schema_filename(cache_key)
        if not path.exists():
            messages.append(f"missing: {path}")
            continue
        expected = serialize_schema(document)
        if path.read_text().rstrip() != expected:
            messages.append(f"drifted: {path}")
    return messages
