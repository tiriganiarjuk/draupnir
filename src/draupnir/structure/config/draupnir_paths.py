"""Where Draupnir's own files are — worked out once, at the entry point, and passed down.

Each entry point resolves the project root a single time and builds this model;
every function that needs one of these locations receives it as a parameter.
"""

from pydantic import BaseModel, ConfigDict


class DraupnirPaths(BaseModel):
    """Draupnir's project root and the files and directories beneath it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root: str
    input_schema_dir: str
    config_schema_dir: str
    input_models_dir: str
    tool_models_dir: str
    nornir_tool_schema_dir: str
