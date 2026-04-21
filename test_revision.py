"""Tests for the revision model (revision.py).

Covers: validation, normalization, parsing, suggestion, and filename formatting.
"""

import pytest
from revision import (
    is_valid_revision,
    normalize_revision,
    parse_revision,
    suggest_next_revision,
    format_for_filename,
)


# ── is_valid_revision ─────────────────────────────────────────────────────────

class TestIsValidRevision:
    @pytest.mark.parametrize("value", [
        "Rev0.1", "Rev0.2", "Rev0.99",
        "RevA", "RevB", "RevZ",
        "RevA.1", "RevA.2", "RevZ.10",
    ])
    def test_valid(self, value):
        assert is_valid_revision(value) is True

    @pytest.mark.parametrize("value", [
        "", "Rev", "Rev0", "RevAA", "Rev1A", "RevA.", "RevA.0",
        "V1", "1.0", "A", "0.1", "Rev0.0",
    ])
    def test_invalid(self, value):
        assert is_valid_revision(value) is False


# ── normalize_revision ────────────────────────────────────────────────────────

class TestNormalizeRevision:
    @pytest.mark.parametrize("input_val,expected", [
        ("A", "RevA"),
        ("B", "RevB"),
        ("0.1", "Rev0.1"),
        ("0.2", "Rev0.2"),
        ("RevA", "RevA"),
        ("RevA.1", "RevA.1"),
        ("Rev0.1", "Rev0.1"),
        (" RevA ", "RevA"),
    ])
    def test_normalizes(self, input_val, expected):
        assert normalize_revision(input_val) == expected

    @pytest.mark.parametrize("input_val", [
        "", "0", "Rev0", "AA", "Rev", "1.0", "RevA.0", "0.0",
    ])
    def test_returns_none(self, input_val):
        assert normalize_revision(input_val) is None


# ── parse_revision ────────────────────────────────────────────────────────────

class TestParseRevision:
    def test_pre_release(self):
        result = parse_revision("Rev0.1")
        assert result == {"base": "0", "sub": 1, "is_release": False, "is_pre_release": True}

    def test_release(self):
        result = parse_revision("RevA")
        assert result == {"base": "A", "sub": None, "is_release": True, "is_pre_release": False}

    def test_post_release(self):
        result = parse_revision("RevA.2")
        assert result == {"base": "A", "sub": 2, "is_release": False, "is_pre_release": False}

    def test_invalid_returns_none(self):
        assert parse_revision("V1") is None


# ── suggest_next_revision ─────────────────────────────────────────────────────

class TestSuggestNextRevision:
    @pytest.mark.parametrize("current,mode,expected", [
        ("Rev0.1", "working", "Rev0.2"),
        ("Rev0.2", "working", "Rev0.3"),
        ("Rev0.1", "release", "RevA"),
        ("RevA", "working", "RevA.1"),
        ("RevA.1", "working", "RevA.2"),
        ("RevA", "release", "RevB"),
        ("RevA.3", "release", "RevB"),
        ("RevB", "working", "RevB.1"),
    ])
    def test_suggestions(self, current, mode, expected):
        assert suggest_next_revision(current, mode) == expected

    def test_invalid_current_raises(self):
        with pytest.raises(ValueError):
            suggest_next_revision("V1", "working")

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            suggest_next_revision("RevA", "unknown")


# ── format_for_filename ───────────────────────────────────────────────────────

class TestFormatForFilename:
    @pytest.mark.parametrize("input_val,expected", [
        ("RevA", "A"),
        ("RevA.1", "A.1"),
        ("Rev0.1", "0.1"),
        ("RevB", "B"),
        ("-", "-"),
        ("", "-"),
        ("SomeOther", "SomeOther"),
    ])
    def test_format(self, input_val, expected):
        assert format_for_filename(input_val) == expected
