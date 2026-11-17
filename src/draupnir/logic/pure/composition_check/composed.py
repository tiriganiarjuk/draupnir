"""Composition check — every loaded file held against the composition limits.

CC=4-8. Runs after loading, over the cache; returns one refusal line per file
that breaks a limit, so a run reports every breach at once.
"""

from pydantic import BaseModel

from draupnir.logic.pure.composition_check.simple import (
    container_limit_text,
    shallowsection_container_count,
)
from draupnir.structure.config.composition_limits import CompositionLimits
from draupnir.structure.gen.input.shallowsection import Shallowsection


def container_limit_violations(
    cache: dict[str, BaseModel], limits: CompositionLimits,
) -> list[str]:
    """One line per shallowsection naming more containers than the limit allows."""
    violations: list[str] = []
    for cache_key, model in cache.items():
        if not isinstance(model, Shallowsection) or model.containers is None:
            continue
        count = shallowsection_container_count(model.containers)
        if count > limits.shallowsection_max_containers:
            violations.append(container_limit_text(cache_key, count, limits))
    return violations
