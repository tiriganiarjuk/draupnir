"""Codegen config loading — through the reader gate into the typed model.

CC=1. Import from ffi (same module) and structure only.
"""

from pathlib import Path

from draupnir.logic.impure.codegen_config.ffi import read_codegen_config
from draupnir.structure.config.codegen_input import CodegenInputConfig


def load_codegen_config(config_path: Path, schema_dir: Path) -> CodegenInputConfig:
    """Load and validate tools/codegen_input.toml. Raises ValueError on validation failure."""
    json_text = read_codegen_config(str(config_path), "codegen-input", str(schema_dir))
    return CodegenInputConfig.model_validate_json(json_text)
