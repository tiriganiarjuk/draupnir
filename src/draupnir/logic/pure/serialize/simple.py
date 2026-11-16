"""Output naming for a whole run — every document under the filename it is written as.

CC=1-3. Pure: compiled documents in, a filename-keyed mapping out.
"""

from draupnir.logic.pure.serialize.primitive import fragment_filename, schema_filename
from draupnir.structure.model.schema_output import FragmentDocument, SchemaDocument


def named_documents(
    schemas: dict[str, SchemaDocument],
    fragments: dict[str, FragmentDocument],
) -> dict[str, SchemaDocument | FragmentDocument]:
    """Key every schema and fragment by its output filename, schemas first."""
    named: dict[str, SchemaDocument | FragmentDocument] = {
        schema_filename(cache_key): document for cache_key, document in schemas.items()
    }
    named.update({fragment_filename(name): document for name, document in fragments.items()})
    return named
