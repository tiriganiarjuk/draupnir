"""A JSON document held as its value, for comparing two documents.

Two JsonDocuments are equal when they hold the same JSON value: the same
keys and values at every depth, whatever the spacing or key order of the
text they were parsed from. The drift check compares a schema as compiled
with the same schema as it stands on disk this way.
"""

from pydantic import ConfigDict, JsonValue, RootModel


class JsonDocument(RootModel[JsonValue]):
    """Any JSON value, parsed from text with model_validate_json."""

    model_config = ConfigDict(frozen=True)
