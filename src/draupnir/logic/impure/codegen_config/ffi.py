"""FFI reader wrapper — Rust-side TOML read + schema validation.

CC=1. Thin wrapper around the PyO3 read_toml_validate_json module (nornir
readers/). Isolated in its own module so a missing compiled reader fails as
"import read_toml_validate_json" rather than inside a larger module.
"""

import read_toml_validate_json

from draupnir.structure.model.tool_outcome import ToolRefusal, ToolResult, ToolSuccess


def read_codegen_config(
    file_path: str, schema_name: str, schema_dir: str,
) -> ToolSuccess | ToolRefusal:
    """Read the codegen config TOML, validate against the named schema, type the result.

    A ToolSuccess carries the validated JSON string in `data`. A
    ToolRefusal carries the failure class in `error.type` and the message
    in `error.message`.
    """
    result = read_toml_validate_json.read(file_path, schema_name, schema_dir)
    return ToolResult.model_validate(result).root
