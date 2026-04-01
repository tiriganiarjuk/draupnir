"""Loader simple — single file loading via gate.

CC=1-3. The loading pipeline for a single Verdandi YAML file:
1. Build filesystem path from root/level/name
2. Pass to Rust PyO3 gate which reads YAML, validates against JSON Schema,
   and returns a JSON string (or raises ValueError on validation failure)
3. Parse JSON into the generated Pydantic input model for that level

The gate step is critical — it catches malformed YAML before Python ever
sees it, and the JSON Schema validation ensures structural correctness.
The generated input models (InputLevel enum → model class) have RootModel
wrappers for all ref fields, so downstream code accesses cache keys via
.root attribute access.
"""

from pathlib import Path

from pydantic import BaseModel

from draupnir.logic.impure.loader.ffi import gate_validate
from draupnir.logic.impure.loader.primitive import level_file_path
from draupnir.structure.config.input_models import InputLevel


def load_one(
    root: Path, level_name: str, name: str, schema_dir: str,
) -> BaseModel:
    """Load a single Verdandi YAML file via gate into a generated input model.

    The gate returns a JSON string (not a dict) to avoid Python dict overhead
    on the PyO3 boundary. model_validate_json parses directly from the string.
    """
    file_path = str(level_file_path(root, level_name, name))
    json_string = gate_validate(file_path, level_name, schema_dir)
    model_class = InputLevel[level_name].value
    return model_class.model_validate_json(json_string)
