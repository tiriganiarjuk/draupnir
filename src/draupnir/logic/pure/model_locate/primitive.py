"""Locate the models draupnir-generate-models writes, and the schemas they come from.

CC=1. A level's input model comes from schemas/input/{level}.schema.json and is
written to gen/input/{level}.py. A Nornir tool schema's model comes from
nornir/schemas/tools/{value}.schema.json and is written to gen/tools/{name}.py,
its Python-safe member name.
"""

from pathlib import PurePath

from draupnir.structure.config.draupnir_paths import DraupnirPaths
from draupnir.structure.config.model_codegen import ModelTarget, NornirToolSchema


def input_model_target(paths: DraupnirPaths, level_name: str) -> ModelTarget:
    """The input model one Verdandi level is generated into, and its schema."""
    return ModelTarget(
        name=level_name,
        schema_file=str(PurePath(paths.input_schema_dir) / f"{level_name}.schema.json"),
        module_file=str(PurePath(paths.input_models_dir) / f"{level_name}.py"),
    )


def tool_model_target(paths: DraupnirPaths, tool_schema: NornirToolSchema) -> ModelTarget:
    """The model one Nornir tool schema is generated into, and its schema."""
    return ModelTarget(
        name=tool_schema.value,
        schema_file=str(PurePath(paths.nornir_tool_schema_dir) / f"{tool_schema.value}.schema.json"),
        module_file=str(PurePath(paths.tool_models_dir) / f"{tool_schema.name}.py"),
    )
