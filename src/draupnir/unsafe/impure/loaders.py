"""YAML file I/O functions.

UNSAFE/IMPURE: File system access, may raise IOError.
"""

from pathlib import Path
from typing import Any

import yaml


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict.

    IMPURE: File system read.
    """
    with path.open() as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = f"{path}: expected YAML mapping, got {type(data).__name__}"
        raise ValueError(msg)
    return data


def load_all_yaml_in_dir(directory: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Load all .yaml files in a directory, returning (path, data) pairs.

    IMPURE: File system access.
    """
    if not directory.exists():
        return []
    return [
        (p, load_yaml_file(p)) for p in sorted(directory.glob("*.yaml"))
    ]
