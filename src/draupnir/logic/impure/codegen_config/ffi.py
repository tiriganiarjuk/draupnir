"""FFI reader wrapper — Rust-side TOML read + schema validation.

CC=1. Thin wrapper around the PyO3 read_toml_validate_json module (nornir
readers/). Isolated in its own module so a missing compiled reader fails as
"import read_toml_validate_json" rather than inside a larger module.
"""

import read_toml_validate_json


def read_codegen_config(file_path: str, schema_name: str, schema_dir: str) -> str:
    """Read the codegen config TOML, validate against the named schema, return a JSON string.

    Raises ValueError on read, parse, schema-load or validation failure.
    """
    return read_toml_validate_json.read(file_path, schema_name, schema_dir)
