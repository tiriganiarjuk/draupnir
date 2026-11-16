"""Typed result of a Nornir reader call.

The contract has two outcomes: a success carrying the validated JSON
string, or a refusal carrying its failure class and message. Each is its
own model, so a result that is neither fails validation where it arrives.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel


class ReaderError(BaseModel):
    """Why the read was refused: the failure class, and the message for people."""

    model_config = ConfigDict(frozen=True)

    type: str
    message: str


class ReaderSuccess(BaseModel):
    """The file was read and matches its schema; `data` is the validated JSON."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[True]
    data: str
    error: None


class ReaderRefusal(BaseModel):
    """The read was refused; `error` says in which class and why."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[False]
    data: None
    error: ReaderError


class ReaderOutcome(RootModel[Annotated[ReaderSuccess | ReaderRefusal, Field(discriminator="ok")]]):
    """What a reader's read() returns."""

    model_config = ConfigDict(frozen=True)
