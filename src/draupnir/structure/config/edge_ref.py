"""Edge reference — intermediate representation for zone-annotated graph edges.

Produced by the graph_build extractors as a typed alternative to raw dicts.
Each EdgeRef carries the dependency target (cache key), the zone it was
found in (required/optional/conditional/direct), the field name in the
parent's zone dict, and for conditional entries: the raw when-condition
RootModel values that will be adapted to ConditionalWhen at collection time.

Frozen because EdgeRefs are produced in bulk by extract_model_refs and
consumed by build_graph — immutability prevents accidental mutation
during the two-pass graph construction.
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
