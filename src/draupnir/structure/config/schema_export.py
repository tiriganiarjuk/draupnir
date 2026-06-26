"""Configuration for JSON Schema export post-processing.

Declares which generated model names require which JSON Schema constraint
patterns, and the field name tuples used in constraint generation.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ExactlyOneConstraintModel(StrEnum):
    """Models requiring oneOf constraint: exactly one conditional keyword present."""

    simplegroup_conditional = "SimplegroupConditionalEntry"
    group_field_conditional = "GroupFieldConditionalEntry"
    group_container_conditional = "GroupContainerConditionalEntry"
    section_container_conditional = "SectionContainerConditionalEntry"
    shallow_field_conditional = "ShallowFieldConditionalEntry"
    shallow_container_conditional = "ShallowContainerConditionalEntry"
    schema_section_conditional = "SchemaSectionConditionalEntry"
    schema_shallow_conditional = "SchemaShallowConditionalEntry"


class AtLeastOneZoneModel(StrEnum):
    """Models requiring anyOf constraint: at least one zone field present."""

    simplegroup = "Simplegroup"
    group = "Group"


class SchemaExportConfig(BaseModel):
    """Derived constants for schema export transforms.

    Precomputes the frozensets and field name tuples that transforms need.
    Instantiated once per pipeline run and passed to transform functions.
    """

    model_config = ConfigDict(frozen=True)

    exactly_one_names: frozenset[str] = frozenset(
        member.value for member in ExactlyOneConstraintModel
    )
    at_least_one_names: frozenset[str] = frozenset(
        member.value for member in AtLeastOneZoneModel
    )
    conditional_fields: tuple[str, ...] = ("only_when", "always_when", "not_when")
    zone_candidate_fields: tuple[str, ...] = (
        "required", "optional", "conditional", "fields", "containers",
    )
