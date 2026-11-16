"""Typed result of a Nornir tool call — a reader or a writer.

Every call ends in one of two outcomes: a success, or a refusal carrying
its failure class and message. Each is its own model, so a result that is
neither fails validation where it arrives.

A success comes in two shapes, by what the tool is for. A reader hands back
the validated JSON string. A writer's effect is the written file, so its
success carries no data.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ToolError(BaseModel):
    """Why the call was refused: the failure class, and the message for people."""

    model_config = ConfigDict(frozen=True)

    type: str
    message: str


class ToolSuccess(BaseModel):
    """The file was read and matches its schema; `data` is the validated JSON."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[True]
    data: str
    error: None


class ToolWritten(BaseModel):
    """The text matched its schema and the file was written; there is no data."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[True]
    data: None
    error: None


class ToolRefusal(BaseModel):
    """The call was refused; `error` says in which class and why."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[False]
    data: None
    error: ToolError


class ToolResult(RootModel[Annotated[ToolSuccess | ToolRefusal, Field(discriminator="ok")]]):
    """What a reader's read() returns."""

    model_config = ConfigDict(frozen=True)


class ToolWriteResult(RootModel[Annotated[ToolWritten | ToolRefusal, Field(discriminator="ok")]]):
    """What a writer's write() returns."""

    model_config = ConfigDict(frozen=True)
