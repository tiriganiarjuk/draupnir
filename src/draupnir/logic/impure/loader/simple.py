"""Loader simple — single file loading via gate.

CC=1-3. Loads one Verdandi YAML file through the Rust gate, then
validates the JSON into a generated input model with string ref fields.
"""

from pathlib import Path

from pydantic import BaseModel

from draupnir.logic.impure.loader.ffi import gate_validate
from draupnir.logic.impure.loader.primitive import level_file_path
from draupnir.structure.config.input_models import InputLevel


def load_one(
    root: Path, level_name: str, name: str, schema_dir: str,
) -> BaseModel:
    """Load a single Verdandi YAML file via gate into a generated input model."""
    file_path = str(level_file_path(root, level_name, name))
    json_string = gate_validate(file_path, level_name, schema_dir)
    model_class = InputLevel[level_name].value
    return model_class.model_validate_json(json_string)
