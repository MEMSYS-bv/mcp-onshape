"""Shared revision model for Onshape MCP tooling.

Canonical revision format:
  Pre-release:   Rev0.1, Rev0.2, Rev0.3, ...
  First release: RevA
  Post-release:  RevA.1, RevA.2, ...
  Next release:  RevB
  Continues:     RevB.1, ..., RevC, ...

All functions expect and return the full label including the "Rev" prefix.
"""

import re

# Matches: Rev0.1, Rev0.2, RevA, RevA.1, RevB, RevB.3, RevZ, RevZ.99
# Groups: (letter_or_zero)(optional .N sub-revision)
_REVISION_RE = re.compile(
    r'^Rev([A-Z]|0)(?:\.(\d+))?$'
)

# Loose pattern: accepts raw values like "A", "0.1", "RevA", "RevA.1"
_LOOSE_RE = re.compile(
    r'^(?:Rev)?([A-Z]|0)(?:\.(\d+))?$'
)


def is_valid_revision(value: str) -> bool:
    """Check whether a string is a valid canonical revision label.

    Valid examples: Rev0.1, Rev0.2, RevA, RevA.1, RevB
    Invalid examples: V1, 1.0, Rev, RevAA, Rev1A, RevA., Rev0
    """
    if not value:
        return False
    m = _REVISION_RE.match(value)
    if not m:
        return False
    base, sub = m.group(1), m.group(2)
    # Rev0 without sub-revision is not valid (must be Rev0.1+)
    if base == '0' and sub is None:
        return False
    # Sub-revision must be >= 1
    if sub is not None and int(sub) < 1:
        return False
    return True


def normalize_revision(value: str) -> str | None:
    """Normalize a revision string to canonical form.

    Accepts loose inputs like "A", "0.1", "RevA", "RevA.1" and returns
    the canonical form ("RevA", "Rev0.1", etc.).

    Returns None if the value cannot be normalized to a valid revision.
    """
    if not value:
        return None
    value = value.strip()
    m = _LOOSE_RE.match(value)
    if not m:
        return None
    base, sub = m.group(1), m.group(2)
    # Build canonical form
    if sub is not None:
        if int(sub) < 1:
            return None
        result = f"Rev{base}.{sub}"
    else:
        if base == '0':
            return None  # Rev0 alone is invalid
        result = f"Rev{base}"
    return result


def parse_revision(value: str) -> dict | None:
    """Parse a canonical revision label into components.

    Returns dict with:
      - base: 'A', 'B', ..., or '0' (pre-release)
      - sub: int or None (sub-revision number)
      - is_release: True if this is a release revision (letter, no sub)
      - is_pre_release: True if base is '0'

    Returns None if the value is not a valid revision.
    """
    if not is_valid_revision(value):
        return None
    m = _REVISION_RE.match(value)
    base = m.group(1)
    sub = int(m.group(2)) if m.group(2) else None
    return {
        'base': base,
        'sub': sub,
        'is_release': base != '0' and sub is None,
        'is_pre_release': base == '0',
    }


def suggest_next_revision(current: str, mode: str = "working") -> str:
    """Suggest the next revision label.

    Args:
        current: Current revision label (canonical form).
        mode: "working" for next intermediate, "release" for next formal release.

    Returns:
        Suggested next revision label, or raises ValueError if current is invalid.
    """
    parsed = parse_revision(current)
    if parsed is None:
        raise ValueError(
            f"Cannot suggest next revision: '{current}' is not a valid revision. "
            f"Valid examples: Rev0.1, RevA, RevA.1, RevB"
        )

    base = parsed['base']
    sub = parsed['sub']

    if mode == "working":
        # Next intermediate: increment sub-revision
        if base == '0':
            # Rev0.1 → Rev0.2, Rev0.2 → Rev0.3
            next_sub = (sub or 0) + 1
            return f"Rev0.{next_sub}"
        else:
            # RevA → RevA.1, RevA.1 → RevA.2
            next_sub = (sub or 0) + 1
            return f"Rev{base}.{next_sub}"

    elif mode == "release":
        # Next formal release: bump to next letter
        if base == '0':
            return "RevA"
        else:
            next_letter = chr(ord(base) + 1)
            if next_letter > 'Z':
                raise ValueError("Revision sequence exhausted (past RevZ).")
            return f"Rev{next_letter}"

    else:
        raise ValueError(f"Unknown mode: '{mode}'. Use 'working' or 'release'.")


def format_for_filename(revision: str) -> str:
    """Format a revision for use in export filenames.

    Ensures the value is suitable for the naming convention:
      ${partNumber}_Rev${revision}-${name}.ext

    Since the convention already adds "Rev" as a prefix, this function
    strips the "Rev" prefix from the canonical label to avoid double-prefix
    like "_RevRevA-".

    If the input is not a valid revision, returns it as-is (fallback).
    """
    if revision and revision.startswith("Rev"):
        return revision[3:]  # "RevA" → "A", "RevA.1" → "A.1", "Rev0.1" → "0.1"
    return revision or "-"
