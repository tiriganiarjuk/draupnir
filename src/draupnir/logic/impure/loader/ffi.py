"""FFI reader wrapper — Rust-side YAML read + schema validation.

CC=1. Thin wrapper around the PyO3 read_yaml_validate_json module (nornir
readers/). The reader reads a YAML file, validates it against the JSON
Schema named by level in schema_dir, and returns the validated data as a
JSON string. The reader must be compiled via `nornir_deploy --build readers`
before draupnir can run.

Isolated in its own module so the import error from a missing compiled
reader is traceable (shows up as "import read_yaml_validate_json" failure
rather than buried in a larger module).
"""

import read_yaml_validate_json


def gate_validate(file_path: str, level_name: str, schema_dir: str) -> str:
    """Call the PyO3 reader for a single file. Returns validated JSON string.

    The reader loads the level's JSON Schema from schema_dir, reads the YAML
    file, validates, and returns the data as a JSON string. Raises ValueError
    if validation fails (malformed YAML or schema violation).
    """
    return read_yaml_validate_json.read(file_path, level_name, schema_dir)
