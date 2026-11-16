"""FFI reader wrapper — Rust-side YAML read + schema validation.

CC=1. Thin wrapper around the PyO3 read_yaml_validate_json module (nornir
readers/). The reader reads a YAML file, validates it against the JSON
Schema named by level in schema_dir, and returns the tool contract:
ok, data, error. The wrapper types that result at once. The reader must be
compiled via `nornir_deploy --build readers` before draupnir can run.

Isolated in its own module so the import error from a missing compiled
reader is traceable (shows up as "import read_yaml_validate_json" failure
rather than buried in a larger module).
"""

import read_yaml_validate_json

from draupnir.structure.model.tool_outcome import ToolRefusal, ToolResult, ToolSuccess


def gate_validate(
    file_path: str, level_name: str, schema_dir: str,
) -> ToolSuccess | ToolRefusal:
    """Call the PyO3 reader for a single file and type its result.

    A ToolSuccess carries the validated JSON string in `data`. A
    ToolRefusal carries the failure class in `error.type` and the message
    in `error.message` (unreadable file, malformed YAML, schema violation).
    """
    result = read_yaml_validate_json.read(file_path, level_name, schema_dir)
    return ToolResult.model_validate(result).root
