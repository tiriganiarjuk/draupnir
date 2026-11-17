"""Every model draupnir-generate-models writes.

CC=1-3. One input model per Verdandi level, in load order, then one model per
Nornir tool schema.
"""

from draupnir.logic.pure.model_locate.primitive import input_model_target, tool_model_target
from draupnir.structure.config.draupnir_paths import DraupnirPaths
from draupnir.structure.config.levels import Level
from draupnir.structure.config.model_codegen import ModelTarget, NornirToolSchema


def model_targets(paths: DraupnirPaths) -> tuple[ModelTarget, ...]:
    """Every model to generate, with the schema each comes from."""
    levels = tuple(input_model_target(paths, level.name) for level in Level)
    tools = tuple(tool_model_target(paths, tool_schema) for tool_schema in NornirToolSchema)
    return levels + tools
