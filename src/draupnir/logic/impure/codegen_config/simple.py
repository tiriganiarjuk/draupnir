"""Codegen config loading — through the reader gate into the typed model.

CC=1-3. Reads tools/codegen_input.toml against its schema in schemas/config/.
"""

from draupnir.logic.impure.codegen_config.ffi import read_codegen_config
from draupnir.logic.pure.schema_locate.primitive import codegen_input_schema
from draupnir.structure.config.codegen_input import CodegenInputConfig
from draupnir.structure.config.draupnir_paths import DraupnirPaths
from draupnir.structure.model.tool_outcome import ToolRefusal


def load_codegen_config(paths: DraupnirPaths) -> CodegenInputConfig | ToolRefusal:
    """Load and validate tools/codegen_input.toml.

    Returns the typed config, or the reader's ToolRefusal when the file
    was refused.
    """
    outcome = read_codegen_config(paths.codegen_config_file, codegen_input_schema(paths))
    if isinstance(outcome, ToolRefusal):
        return outcome
    return CodegenInputConfig.model_validate_json(outcome.data)
