"""Integration tests: load real YAML files and validate into Pydantic models.

Proves that model shapes match actual YAML on disk. If these tests fail,
the structures don't match reality and must be updated before building
anything on top of them.
"""

from pathlib import Path

import yaml

from draupnir.structures import (
    RawArray,
    RawComposed,
    RawGroup,
    RawPrimitive,
    RawSection,
)

TOOLCOMPOSE = Path("/Users/johnny/.ai/spaces/bragi/standards/toolcompose")


def _load(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


# =============================================================================
# PRIMITIVES — every single one must parse
# =============================================================================


class TestAllPrimitives:
    def test_every_primitive_validates(self) -> None:
        """All 54+ primitives must parse into RawPrimitive."""
        primitives_dir = TOOLCOMPOSE / "primitives"
        failures = []
        count = 0
        for path in sorted(primitives_dir.glob("*.yaml")):
            count += 1
            try:
                RawPrimitive.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No primitives found"
        assert failures == [], f"Failed primitives:\n" + "\n".join(failures)

    def test_path_exists_absolute_shape(self) -> None:
        """Spot-check: path with format, validation, not constraint chain."""
        data = _load(TOOLCOMPOSE / "primitives/path_exists_absolute.yaml")
        p = RawPrimitive.model_validate(data)
        assert p.name == "path_exists_absolute"
        assert p.type == "path_allowed_absolute"
        assert p.format == "path_exists_absolute"
        assert p.validation is not None

    def test_path_allowed_absolute_shape(self) -> None:
        """Spot-check: path with not constraint."""
        data = _load(TOOLCOMPOSE / "primitives/path_allowed_absolute.yaml")
        p = RawPrimitive.model_validate(data)
        assert p.not_constraint is not None
        assert p.not_constraint.ref == "PATH_BLOCKLIST"
        assert p.pattern == "^/"

    def test_dispatch_mode_shape(self) -> None:
        """Spot-check: enum type."""
        data = _load(TOOLCOMPOSE / "primitives/dispatch_mode.yaml")
        p = RawPrimitive.model_validate(data)
        assert p.enum is not None
        assert "batch" in p.enum

    def test_instruction_text_shape(self) -> None:
        """Spot-check: semantic constraint."""
        data = _load(TOOLCOMPOSE / "primitives/instruction_text.yaml")
        p = RawPrimitive.model_validate(data)
        assert p.semantic is not None
        assert p.semantic.intent != ""
        assert len(p.semantic.checks) > 0


# =============================================================================
# COMPOSED — every single one must parse
# =============================================================================


class TestAllComposed:
    def test_every_composed_validates(self) -> None:
        """All composed YAMLs must parse into RawComposed."""
        composed_dir = TOOLCOMPOSE / "composed"
        failures = []
        count = 0
        for path in sorted(composed_dir.glob("*.yaml")):
            count += 1
            try:
                RawComposed.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No composed found"
        assert failures == [], f"Failed composed:\n" + "\n".join(failures)


# =============================================================================
# GROUPS + SUPERGROUPS — every single one must parse
# =============================================================================


class TestAllGroups:
    def test_every_group_validates(self) -> None:
        """All group YAMLs must parse into RawGroup."""
        groups_dir = TOOLCOMPOSE / "groups"
        failures = []
        count = 0
        for path in sorted(groups_dir.glob("*.yaml")):
            count += 1
            try:
                RawGroup.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No groups found"
        assert failures == [], f"Failed groups:\n" + "\n".join(failures)

    def test_every_supergroup_validates(self) -> None:
        """All supergroup YAMLs must parse into RawGroup (same model)."""
        sg_dir = TOOLCOMPOSE / "supergroups"
        failures = []
        count = 0
        for path in sorted(sg_dir.glob("*.yaml")):
            count += 1
            try:
                RawGroup.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No supergroups found"
        assert failures == [], f"Failed supergroups:\n" + "\n".join(failures)


# =============================================================================
# ARRAYS + SUPERARRAYS — every single one must parse
# =============================================================================


class TestAllArrays:
    def test_every_array_validates(self) -> None:
        """All array YAMLs must parse into RawArray."""
        arrays_dir = TOOLCOMPOSE / "arrays"
        failures = []
        count = 0
        for path in sorted(arrays_dir.glob("*.yaml")):
            count += 1
            try:
                RawArray.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No arrays found"
        assert failures == [], f"Failed arrays:\n" + "\n".join(failures)

    def test_every_superarray_validates(self) -> None:
        """All superarray YAMLs must parse into RawArray (same model)."""
        sa_dir = TOOLCOMPOSE / "superarrays"
        failures = []
        count = 0
        for path in sorted(sa_dir.glob("*.yaml")):
            count += 1
            try:
                RawArray.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No superarrays found"
        assert failures == [], f"Failed superarrays:\n" + "\n".join(failures)


# =============================================================================
# SECTIONS — every single one must parse
# =============================================================================


class TestAllSections:
    def test_every_section_validates(self) -> None:
        """All section YAMLs must parse into RawSection."""
        sections_dir = TOOLCOMPOSE / "sections"
        failures = []
        count = 0
        for path in sorted(sections_dir.glob("*.yaml")):
            count += 1
            try:
                RawSection.model_validate(_load(path))
            except Exception as e:
                failures.append(f"{path.name}: {e}")
        assert count > 0, "No sections found"
        assert failures == [], f"Failed sections:\n" + "\n".join(failures)
