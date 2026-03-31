"""Tree analysis — single-expression helpers.

CC=1 functions for output preparation. No branching, no iteration.
"""

from draupnir.structure.model.schema_output import SchemaArray, SchemaObject


def wrap_array_as_object(array: SchemaArray) -> SchemaObject:
    """Wrap a SchemaArray in a SchemaObject with an 'items' property.

    TOML root is always a table — bare arrays can't be represented.
    Include files use 'items' as the key for their array content.
    """
    return SchemaObject(
        title=array.title,
        description=array.description,
        properties={"items": array},
        required=("items",),
        additional_properties=False,
    )
