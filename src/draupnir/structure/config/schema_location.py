"""Where a schema file is: its name and the directory that holds it.

A Nornir reader or writer validates against `{directory}/{name}.schema.json`.
"""

from pydantic import BaseModel, ConfigDict


class SchemaLocation(BaseModel):
    """One schema, named the way the Nornir tools take it."""

    model_config = ConfigDict(frozen=True)

    name: str
    directory: str
