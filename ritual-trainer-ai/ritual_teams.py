"""Patron display names for match metadata team indexes and Source 2 entity teams.

Deadlock match metadata commonly uses sides 0/1; replay entity enums use 2/3.
These two numbering systems must not be confused. Unknown IDs are not guessed.
"""
from __future__ import annotations

PATRONS = {0: "The Hidden King", 1: "The Archmother", 2: "The Hidden King", 3: "The Archmother"}


def patron_name(team: object) -> str:
    """Readable Patron label, preserving uncertainty for unexpected values."""
    if isinstance(team, bool):
        return "Unknown patron"
    try:
        key = int(team)
    except (ValueError, TypeError):
        return "Unknown patron"
    return PATRONS.get(key, "Unknown patron")
