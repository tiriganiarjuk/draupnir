"""Composition check — one shallowsection's containers, counted and reported.

CC=1-3. A shallowsection's containers sit in three zones (required, optional,
conditional); the limit is on their total, which no single zone's schema can see.
"""

from draupnir.structure.config.composition_limits import CompositionLimits
from draupnir.structure.gen.input.shallowsection import ShallowContainers


def shallowsection_container_count(containers: ShallowContainers) -> int:
    """Every container a shallowsection names, across its three zones."""
    zones = (containers.required, containers.optional, containers.conditional)
    return sum(len(zone.root or {}) for zone in zones if zone is not None)


def container_limit_text(cache_key: str, count: int, limits: CompositionLimits) -> str:
    """The refusal for a shallowsection holding more containers than the limit."""
    return (
        f"{cache_key}: names {count} containers; a shallowsection holds at most "
        f"{limits.shallowsection_max_containers} — compose deeper with section/ and groups"
    )
