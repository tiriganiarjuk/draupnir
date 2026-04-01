"""Edge reference — zone-annotated dependency between graph nodes.

Carries the zone metadata (required/optional/conditional/direct),
the field name in the parent dict, and raw when conditions for
conditional entries.
"""

from pydantic import BaseModel, ConfigDict


class EdgeRef(BaseModel):
    """A single zone-annotated reference from parent to child node."""

    model_config = ConfigDict(frozen=True)

    target: str
    zone: str
    name: str
    only_when: BaseModel | None = None
    always_when: BaseModel | None = None
    not_when: BaseModel | None = None
