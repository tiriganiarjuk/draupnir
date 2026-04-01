"""FFI gate wrapper — Rust-side YAML validation.

CC=1. Thin wrapper around the PyO3 gate_verdandi_input module. The gate
reads a YAML file, validates it against the appropriate JSON Schema for
its level, and returns the validated data as a JSON string. This Rust
gate must be compiled via nornir_deploy before draupnir can run.

Isolated in its own module so the import error from a missing compiled
gate is traceable (shows up as "import gate_verdandi_input" failure
rather than buried in a larger module).
"""

import gate_verdandi_input


def gate_validate(file_path: str, level_name: str, schema_dir: str) -> str:
    """Call the PyO3 gate for a single file. Returns validated JSON string.

    The gate loads the level's JSON Schema from schema_dir, reads the YAML
    file, validates, and returns the data as a JSON string. Raises ValueError
    if validation fails (malformed YAML or schema violation).
    """
    return gate_verdandi_input.validate(file_path, level_name, schema_dir)
