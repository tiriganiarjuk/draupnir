"""FFI writer wrapper — Rust-side JSON validation + file write.

CC=1. Thin wrapper around the PyO3 write_json_validate_json module (nornir
text_writers/). The writer validates the JSON text against the given schema,
then writes it to the file exactly as given, ended with a line break.
Isolated in its own module so a missing compiled writer fails as
"import write_json_validate_json" rather than inside a larger module.
"""

import write_json_validate_json

from draupnir.structure.config.schema_location import SchemaLocation
from draupnir.structure.model.tool_outcome import ToolRefusal, ToolWriteResult, ToolWritten


def write_json_text(
    json_text: str, file_path: str, schema: SchemaLocation,
) -> ToolWritten | ToolRefusal:
    """Validate JSON text against the schema and write it; type the result.

    A ToolWritten means the file is on disk. A ToolRefusal carries the
    failure class in `error.type` and the message in `error.message`, and
    nothing was written.
    """
    result = write_json_validate_json.write(json_text, file_path, schema.name, schema.directory)
    return ToolWriteResult.model_validate(result).root
