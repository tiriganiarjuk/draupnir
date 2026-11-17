"""Composition limits — rules of the Verdandi hierarchy that a JSON Schema cannot hold.

A schema validates one file's shape; a limit that spans sibling zones of a
file, or a fact about the loaded hierarchy as a whole, is checked by Draupnir
after loading, and a file that breaks one stops the run.
"""

from pydantic import BaseModel, ConfigDict


class CompositionLimits(BaseModel):
    """The limits Draupnir checks after loading, beyond what the input schemas enforce."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    shallowsection_max_containers: int = 3
