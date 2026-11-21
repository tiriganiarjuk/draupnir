"""What draupnir-generate-models generates: one model module per schema.

Every Verdandi level has an input schema and an input model; every Nornir tool
whose output Draupnir reads has a tool schema and a tool model. Both sets are
closed — Level and NornirToolSchema — and each schema's file and its module's
file are computed from its name, so nothing here is configured by hand.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class NornirToolSchema(StrEnum):
    """The Nornir tool schemas whose output Draupnir validates into a model.

    The value is the file name under nornir/schemas/tools/ without .schema.json.
    """

    directory_listing = "directory-listing"
    directory_write_request = "directory-write-request"
    directory_write_report = "directory-write-report"


class ModelTarget(BaseModel):
    """One model to generate: the schema it comes from and the module it is written to."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    schema_file: str
    module_file: str
