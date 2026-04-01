"""Codegen clean primitives — fix code-generation artifacts.

CC=1. No branching. No cross-module dependencies.

Fixes two code-generation artifacts from datamodel-code-generator. These
are not stylistic preferences — both cause runtime failures if left in place:

1. The __future__ annotations import makes all type hints strings at runtime,
   breaking Pydantic's model_validate which needs real types for validation.
2. The RootModel name collection is the first step of the constraint stripping
   pipeline (see composed.py for why constraints need stripping).
"""

import re


def strip_future_annotations(content: str) -> str:
    """Remove __future__ annotations import added by codegen.

    Python 3.13 does not need this import, and it breaks Pydantic
    validation by making all annotations strings at runtime.
    """
    marker = "__future__"
    target = f"from {marker} import annotations\n\n"
    return content.replace(target, "")


def collect_rootmodel_names(content: str) -> set[str]:
    """Find all class names that extend RootModel via regex.

    These names feed the simple-level classifier that decides which
    Annotated fields need constraint stripping. The regex matches
    'class FooBar(RootModel' and captures 'FooBar'.
    """
    return set(re.findall(r"class (\w+)\(RootModel", content))
