"""Source files — what makes a listed file a Verdandi file.

CC=1-3. A Verdandi file is {level}/{name}.yaml: one directory deep, under a
known level, with a .yaml suffix. Anything else in a project's source tree is a
stray.
"""

from pathlib import PurePath, PurePosixPath

from draupnir.structure.config.verdandi_manifest import LevelName, SweptFiles, VerdandiLayout


def is_level_file(path: PurePosixPath, layout: VerdandiLayout) -> bool:
    """Whether a path relative to the source root is {level}/{name}{suffix} under a known level."""
    return (
        len(path.parts) == 2
        and path.suffix == layout.file_suffix
        and path.parts[0] in LevelName.__members__
    )


def stray_files_text(source_root: PurePath, files: SweptFiles) -> str:
    """The refusal for a source tree holding files that are not Verdandi files, naming each."""
    named = "\n".join(f"  {stray.path}" for stray in files.strays)
    return (
        f"SWEEP ERROR: {source_root}: {len(files.strays)} file(s) are not "
        f"{{level}}/{{name}} Verdandi files under a known level:\n{named}"
    )
