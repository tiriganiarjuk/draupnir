"""Pipeline configuration models.

Frozen Pydantic models for pipeline mode and resolved paths.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict


class PipelineMode(str, Enum):
    """Pipeline execution mode."""

    generate = "generate"
    check = "check"
    list_schemas = "list"
    fragments = "fragments"


class PipelineArgs(BaseModel):
    """Raw CLI arguments before resolution."""

    model_config = ConfigDict(frozen=True)

    check: bool = False
    list_schemas: bool = False
    fragments: bool = False
    project: str | None = None
    verdandi_dir: str | None = None
    output_dir: str | None = None
    workspace: str | None = None


class PipelineContext(BaseModel):
    """Resolved pipeline context — mode + paths."""

    model_config = ConfigDict(frozen=True)

    mode: PipelineMode
    verdandi: str
    output: str
