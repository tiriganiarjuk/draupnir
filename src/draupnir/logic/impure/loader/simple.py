"""Loader simple — single file loading via gate.

CC=1-3. The loading pipeline for a single Verdandi YAML file:
1. Build filesystem path from root/level/name
2. Pass to Rust PyO3 gate which reads YAML, validates against JSON Schema,
   and returns a typed outcome: a success carrying the JSON string, or a
   refusal carrying its failure class and message
3. On success, parse JSON into the generated Pydantic input model for that
   level; a refusal is handed back to the caller as it is

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
from draupnir.structure.model.tool_outcome import ToolRefusal


def load_one(
    root: Path, level_name: str, name: str, schema_dir: str,
) -> BaseModel | ToolRefusal:
    """Load a single Verdandi YAML file via gate into a generated input model.

    Returns the input model, or the gate's ToolRefusal when the file was
    refused. model_validate_json parses directly from the validated JSON
    string the success carries.
    """
    file_path = str(level_file_path(root, level_name, name))
    outcome = gate_validate(file_path, level_name, schema_dir)
    if isinstance(outcome, ToolRefusal):
        return outcome
    model_class = InputLevel[level_name].value
    return model_class.model_validate_json(outcome.data)
