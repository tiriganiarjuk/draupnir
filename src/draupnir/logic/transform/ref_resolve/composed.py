"""Ref resolution — replace string cache keys with cached models.

Walks a raw YAML dict and replaces any string value that exists as a
cache key with the corresponding cached model. This is the explicit
transform that replaces implicit BeforeValidator ref resolution.

Runs BEFORE model_validate, so Pydantic sees model instances where
ref fields are declared, not strings.
"""

from pydantic import BaseModel

type YamlLeaf = str | int | bool | None
type YamlValue = YamlLeaf | dict[str, YamlValue] | list[YamlValue]
type YamlContainer = dict[str, YamlValue] | list[YamlValue]


def resolve_dict_refs(
    data: dict[str, YamlValue],
    cache: dict[str, BaseModel],
) -> list[YamlContainer]:
    """Resolve string refs in dict values. Returns nested containers for stack."""
    nested: list[YamlContainer] = []
    for field_name, value in data.items():
        if isinstance(value, str) and value in cache:
            data[field_name] = cache[value]
        elif isinstance(value, (dict, list)):
            nested.append(value)
    return nested


def resolve_list_refs(
    data: list[YamlValue],
    cache: dict[str, BaseModel],
) -> list[YamlContainer]:
    """Resolve string refs in list items. Returns nested containers for stack."""
    nested: list[YamlContainer] = []
    for index, value in enumerate(data):
        if isinstance(value, str) and value in cache:
            data[index] = cache[value]
        elif isinstance(value, (dict, list)):
            nested.append(value)
    return nested


def resolve_refs(
    data: dict[str, YamlValue],
    cache: dict[str, BaseModel],
) -> dict[str, YamlValue]:
    """Replace string cache keys with cached models throughout a raw YAML dict.

    Uses an explicit stack to walk nested dicts and lists. Mutates and
    returns the input dict.
    """
    stack: list[YamlContainer] = [data]
    while stack:
        container = stack.pop()
        if isinstance(container, dict):
            stack.extend(resolve_dict_refs(container, cache))
        elif isinstance(container, list):
            stack.extend(resolve_list_refs(container, cache))
    return data
