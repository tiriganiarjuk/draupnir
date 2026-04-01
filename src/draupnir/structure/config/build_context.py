"""Build context — shared state for the compile loop.

Holds two dicts:
- built: what parents embed. SchemaRef for shared nodes (in-degree >= 2),
  full schema otherwise. This is what gets slotted into parent schemas.
- full: always the full built result. For destructuring — when a builder
  needs to read fields from a child (e.g. build_element reads base.type).
"""

from pydantic import BaseModel, Field


class BuildContext(BaseModel):
    """Mutable compile-loop accumulator.

    built: parent-facing results (SchemaRef for shared, full otherwise)
    full: always-full results (for destructuring child properties)

    Not frozen — the compile loop mutates both dicts during iteration.
    """

    built: dict[str, BaseModel] = Field(default_factory=dict)
    full: dict[str, BaseModel] = Field(default_factory=dict)
