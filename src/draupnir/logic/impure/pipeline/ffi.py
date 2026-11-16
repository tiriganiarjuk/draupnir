"""FFI reader wrapper — Rust-side JSON read + schema validation.

CC=1. Thin wrapper around the PyO3 read_json_validate_json module (nornir
readers/). Isolated in its own module so a missing compiled reader fails as
"import read_json_validate_json" rather than inside a larger module.
"""

import read_json_validate_json

from draupnir.structure.config.schema_location import SchemaLocation
from draupnir.structure.model.tool_outcome import ToolRefusal, ToolResult, ToolSuccess


def read_json_text(file_path: str, schema: SchemaLocation) -> ToolSuccess | ToolRefusal:
    """Read a JSON file, validate it against the schema, type the result.

    A ToolSuccess carries the validated JSON string in `data`. A
    ToolRefusal carries the failure class in `error.type` and the message
    in `error.message`.
    """
    result = read_json_validate_json.read(file_path, schema.name, schema.directory)
    return ToolResult.model_validate(result).root
