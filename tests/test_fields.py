"""Tests for field-level Verdandi models."""

import pytest
from pydantic import ValidationError

from draupnir.structures.fields import (
    Atom,
    Element,
    Enum,
    Pattern,
    Union_,
)


@pytest.fixture
def pattern_relative():
    return Pattern(title="Relative", regex=r"^\.", description="Relative path prefix")


@pytest.fixture
def pattern_traversal():
    return Pattern(title="Traversal", regex=r"\.\.", description="Path traversal")


@pytest.fixture
def cache(pattern_relative, pattern_traversal):
    return {
        "pattern/relative": pattern_relative,
        "pattern/traversal": pattern_traversal,
    }


class TestPattern:
    def test_validates_from_dict(self):
        p = Pattern.model_validate(
            {"title": "Test", "regex": r"^\.", "description": "test"},
        )
        assert p.regex == r"^\."
        assert p.description == "test"

    def test_is_frozen(self):
        p = Pattern(title="Test", regex=".", description="test")
        with pytest.raises(ValidationError):
            p.regex = "new"  # type: ignore[misc]

    def test_rejects_missing_regex(self):
        with pytest.raises(ValidationError):
            Pattern.model_validate({"title": "Test", "description": "test"})


class TestAtom:
    def test_resolves_pattern_from_cache(self, cache, pattern_relative):
        atom = Atom.model_validate(
            {
                "title": "Test",
                "type": "string",
                "pattern": "pattern/relative",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert atom.pattern is pattern_relative

    def test_resolves_excludes_from_cache(
        self, cache, pattern_traversal
    ):
        atom = Atom.model_validate(
            {
                "title": "Test",
                "type": "string",
                "excludes": ["pattern/traversal"],
                "description": "test",
            },
            context={"cache": cache},
        )
        assert atom.excludes is not None
        assert atom.excludes[0] is pattern_traversal

    def test_accepts_integer_type(self):
        atom = Atom.model_validate(
            {"title": "Test", "type": "integer", "description": "test"},
            context={"cache": {}},
        )
        assert atom.type == "integer"

    def test_rejects_invalid_type(self):
        with pytest.raises(ValidationError):
            Atom.model_validate(
                {"title": "Test", "type": "float", "description": "test"},
                context={"cache": {}},
            )

    def test_rejects_missing_cache_ref(self):
        with pytest.raises(ValidationError):
            Atom.model_validate(
                {
                    "title": "Test",
                    "type": "string",
                    "pattern": "pattern/nonexistent",
                    "description": "test",
                },
                context={"cache": {}},
            )


class TestEnum:
    def test_validates_string_values(self):
        e = Enum.model_validate(
            {"title": "Test", "values": ["batch", "full"], "description": "test"},
        )
        assert e.values == ("batch", "full")

    def test_accepts_mixed_value_types(self):
        e = Enum.model_validate(
            {"title": "Test", "values": ["text", 42, True], "description": "test"},
        )
        assert len(e.values) == 3


class TestElement:
    def test_resolves_inherits_from_cache(self, cache):
        atom = Atom.model_validate(
            {"title": "Base", "type": "string", "description": "base"},
            context={"cache": cache},
        )
        cache["atom/test"] = atom
        elem = Element.model_validate(
            {
                "title": "Test",
                "inherits": "atom/test",
                "format": "exists",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert elem.inherits is atom

    def test_accepts_enum_inherits(self, cache):
        enum = Enum(title="Test", values=("a", "b"), description="test")
        cache["enum/test"] = enum
        elem = Element.model_validate(
            {
                "title": "Test",
                "inherits": "enum/test",
                "format": "exists",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert elem.inherits is enum

    def test_mandatory_without_format(self, cache):
        atom = Atom.model_validate(
            {"title": "Base", "type": "string", "description": "base"},
            context={"cache": cache},
        )
        cache["atom/test"] = atom
        elem = Element.model_validate(
            {
                "title": "Test",
                "inherits": "atom/test",
                "required": "mandatory",
                "description": "test",
            },
            context={"cache": cache},
        )
        assert elem.required == "mandatory"
        assert elem.format is None


class TestUnion:
    def test_resolves_members_from_cache(self, cache):
        atom_a = Atom.model_validate(
            {"title": "A", "type": "string", "description": "a"},
            context={"cache": cache},
        )
        atom_b = Atom.model_validate(
            {"title": "B", "type": "integer", "description": "b"},
            context={"cache": cache},
        )
        cache["atom/a"] = atom_a
        cache["atom/b"] = atom_b
        u = Union_.model_validate(
            {
                "title": "Test",
                "union": ["atom/a", "atom/b"],
                "description": "test",
            },
            context={"cache": cache},
        )
        assert u.union[0] is atom_a
        assert u.union[1] is atom_b

    def test_rejects_wrong_tier_ref(self, cache):
        """Union members must be atom/enum/element — not patterns."""
        cache["pattern/test"] = Pattern(
            title="Test", regex=".", description="test",
        )
        with pytest.raises(ValidationError):
            Union_.model_validate(
                {
                    "title": "Test",
                    "union": ["pattern/test"],
                    "description": "test",
                },
                context={"cache": cache},
            )
