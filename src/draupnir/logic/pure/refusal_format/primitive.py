"""Refusal formatting — a refused tool call as one line of text.

CC=1. Pure: a ToolRefusal in, a string out.
"""

from draupnir.structure.model.tool_outcome import ToolRefusal


def refusal_text(refusal: ToolRefusal) -> str:
    """One line for a refused call: the failure class, then the message."""
    return f"{refusal.error.type}: {refusal.error.message}"
