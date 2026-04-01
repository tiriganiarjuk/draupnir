"""Supply-driven loader — FFI gate wrapper.

FFI level (CC=1). Wraps the PyO3 gate_verdandi_input module.
The gate is a required dependency — import failure means it's not compiled.
"""

import gate_verdandi_input


def gate_validate(file_path: str, level_name: str, schema_dir: str) -> str:
    """Call the PyO3 gate. Reads file, validates, returns JSON string. Raises ValueError on failure."""
    return gate_verdandi_input.validate(file_path, level_name, schema_dir)
