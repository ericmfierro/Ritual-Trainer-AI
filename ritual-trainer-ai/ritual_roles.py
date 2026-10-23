"""Flexible Deadlock hero roles for farm-aware coaching, not official classes.

Roles describe a player's intended economy and team responsibilities.
Heroes and roles are flexible; a hero can fill several jobs depending on the build.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CombatRole:
    name: str
    heroes: tuple[str, ...]
    coaching_angle: str
    umbrella: str
    farm_priority: str


AUTO_ROLE = "Auto-suggest from hero"
ROLES: tuple[CombatRole, ...] = (
    CombatRole(
        "Hard Carry",
        ("Lady Geist", "Mirage", "Infernus", "Wraith", "Seven"),
        "Prioritize efficient, safe soul income while tracking item timings; join fights when the likely team value justifies the opportunity cost of missed farm. Evaluate scaling and teamfight impact rather than KDA alone.",
        "Carries",
        "Highest farm priority; typically needs sustained souls to become a late-game win condition.",
    ),
    CombatRole(
        "Tempo / Off-Carry",
        ("Haze", "Warden", "The Drifter", "Pocket"),
        "Balance farm with earlier power spikes, purposeful rotations, picks, and map pressure. Don't recommend AFK farming when a high-value tempo play is available.",
        "Carries",
        "High but flexible farm priority; converts earlier item/ability timings into pressure.",
    ),
    CombatRole(
        "Frontliner / Space Creator",
        ("Abrams", "Bebop", "Mo & Krill"),
        "Evaluate engage timing, survivability, crowd control, objective presence, and how effectively the player creates space for teammates. Do not judge contributions by raw damage or souls alone.",
        "Frontliners / Space Creators",
        "Moderate / situational farm priority; teamfight disruption and space creation matter.",
    ),
    CombatRole(
        "Support & Utility",
        ("Ivy", "Dynamo", "Kelvin", "Viscous", "McGinnis", "Paige"),
        "Evaluate assists, crowd control, healing or protection when available, team setup, objective pressure, and good use of limited souls. Don't punish low farm or low damage without considering support value.",
        "Supports & Utility",
        "Lower farm priority; valuable impact can come from base abilities, utility and enabling carries.",
    ),
)

ROLE_BY_NAME = {role.name: role for role in ROLES}
ROLE_OPTIONS = (AUTO_ROLE,) + tuple(ROLE_BY_NAME)


def _canonical_hero(name: str) -> str:
    cleaned = " ".join(str(name).strip().casefold().replace("&", "and").split())
    aliases = {
        "drifter": "the drifter",
        "mo and krill": "mo and krill",
    }
    return aliases.get(cleaned, cleaned)


def suggested_roles(hero: str) -> list[str]:
    """Examples are suggestions, never proof of actual farm priority."""
    key = _canonical_hero(hero)
    return [role.name for role in ROLES
            if any(_canonical_hero(example) == key for example in role.heroes)]


def resolve_role(hero: str, preference: str) -> dict[str, object]:
    candidates = suggested_roles(hero)
    if preference == AUTO_ROLE:
        name = candidates[0] if candidates else "Not specified"
        source = "suggested from hero examples (not a confirmed in-match role)" if candidates else "hero not in curated examples"
    elif preference in ROLE_BY_NAME:
        name = preference
        source = "chosen by the player"
    else:
        name = "Not specified"
        source = "not specified"
    role = ROLE_BY_NAME.get(name)
    return {
        "hero": hero,
        "role": name,
        "source": source,
        "other_plausible_roles": [r for r in candidates if r != name],
        "coaching_angle": role.coaching_angle if role else "Check the actual build, farm distribution, and team responsibilities.",
        "umbrella": role.umbrella if role else "Unknown",
        "farm_priority": role.farm_priority if role else "Unknown; don't assume a farm priority.",
        "role_is_flexible": True,
    }
