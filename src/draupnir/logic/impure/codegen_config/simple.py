"""Codegen config loading — through the reader gate into the typed model.

CC=1-3. Import from ffi (same module) and structure only.
"""

from pathlib import Path

from draupnir.logic.impure.codegen_config.ffi import read_codegen_config
from draupnir.structure.config.codegen_input import CodegenInputConfig
from draupnir.structure.model.tool_outcome import ToolRefusal


def load_codegen_config(
    config_path: Path, schema_dir: Path,
) -> CodegenInputConfig | ToolRefusal:
    """Load and validate tools/codegen_input.toml.

    Returns the typed config, or the reader's ToolRefusal when the file
    was refused.
    """
    outcome = read_codegen_config(str(config_path), "codegen-input", str(schema_dir))
    if isinstance(outcome, ToolRefusal):
        return outcome
    return CodegenInputConfig.model_validate_json(outcome.data)
