"""Field extension models: SemanticBlock, ConstraintRule.

These are the sub-models carried by VerdandiField for optional semantic
and constraint metadata. Defined separately because VerdandiField lives
in simple_containers.py (containers need it in their ref aliases) and
importing these sub-models from a separate module avoids circular imports.
"""

from pydantic import BaseModel, ConfigDict, Field as PydanticField


class SemanticBlock(BaseModel):
    """Semantic intent and validation guidance for a field."""

    model_config = ConfigDict(frozen=True)

    intent: str | None = None
    checks: tuple[str, ...] | None = None
    anti_patterns: tuple[str, ...] | None = None
    severity: str | None = None


class ConstraintRule(BaseModel):
    """Cross-field validation rule carried by a field."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    rule: str
    severity: str
    reason: str
    field: str | None = None
    order: str | None = None
    values: tuple[str, ...] | None = PydanticField(default=None, alias="in")
