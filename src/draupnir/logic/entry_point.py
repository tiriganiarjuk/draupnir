"""Draupnir entry point — thin wiring between CLI and orchestrate.

Entry point level (CC=1-2).
"""

from draupnir.logic.orchestrate.compile.orchestrate import run_pipeline as _orchestrate_run_pipeline
from draupnir.structure.config.pipeline import PipelineArgs


def run_pipeline(args: PipelineArgs) -> int:
    """Bridge CLI arguments to the orchestrate pipeline."""
    return _orchestrate_run_pipeline(args)
