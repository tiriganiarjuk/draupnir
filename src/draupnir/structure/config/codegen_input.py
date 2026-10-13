"""Codegen input configuration — the typed window onto tools/codegen_input.toml.

The TOML is validated against schemas/config/codegen-input.schema.json by the
reader gate before it reaches this model; the schema fixes the level-name key
set and the module-path shape, this model fixes the Python types.
"""

from pydantic import BaseModel, ConfigDict


class CodegenInputConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    levels: dict[str, str]
