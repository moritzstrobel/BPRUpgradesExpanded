from __future__ import annotations

import re
from functools import lru_cache

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from vanilla_upgrade_layout import (
    VANILLA_ROOT,
    _direct_child,
    _direct_scalar,
    _read_blocks,
    _refkey,
    vanilla_general_setup_upgrades,
)

VANILLA_NPCS = VANILLA_ROOT / "NPCPrototypes.cfg"
TECHNICIAN_TEMPLATE_SIDS = {"TechnicianNPC", "AllTechnicianNPC"}


def _upgrade_children(upgrades: list[str] | None) -> list[list[str]]:
    """Read numeric and [*] entries from an NPC Upgrades struct."""
    if not upgrades:
        return []
    result: list[list[str]] = []
    index = 1
    while index < len(upgrades) - 1:
        if not re.match(r"\s*\[(?:\d+|\*)\]\s*:\s*struct\.begin", upgrades[index]):
            index += 1
            continue
        child = [upgrades[index]]
        depth = 1
        index += 1
        while index < len(upgrades) and depth:
            child.append(upgrades[index])
            stripped = upgrades[index].strip()
            if "struct.begin" in stripped:
                depth += 1
            if stripped == "struct.end":
                depth -= 1
            index += 1
        result.append(child)
    return result


def _upgrade_entries(block: list[str]) -> list[tuple[str, bool]]:
    """Read one NPC's direct Upgrades array."""
    result: list[tuple[str, bool]] = []
    for child in _upgrade_children(_direct_child(block, "Upgrades")):
        sid = _direct_scalar(child, "UpgradePrototypeSID")
        if not sid or sid == "empty":
            continue
        enabled = (_direct_scalar(child, "Enabled") or "false").lower() == "true"
        result.append((sid, enabled))
    return result


def _effective_scalar(blocks: dict[str, list[str]], sid: str, name: str) -> str | None:
    seen: set[str] = set()
    current = sid
    while current and current not in seen:
        seen.add(current)
        block = blocks.get(current)
        if not block:
            return None
        value = _direct_scalar(block, name)
        if value is not None:
            return value
        current = _refkey(block)
    return None


def _effective_upgrade_entries(blocks: dict[str, list[str]], sid: str) -> list[tuple[str, bool]]:
    """Resolve the first Upgrades array in the NPC refkey chain.

    Vanilla child structs that do not define Upgrades inherit their parent's
    complete array. If a child defines Upgrades, that array is the effective
    weapon-upgrade capability list for that NPC.
    """
    seen: set[str] = set()
    current = sid
    while current and current not in seen:
        seen.add(current)
        block = blocks.get(current)
        if not block:
            return []
        if _direct_child(block, "Upgrades") is not None:
            return _upgrade_entries(block)
        current = _refkey(block)
    return []


@lru_cache(maxsize=1)
def vanilla_technician_upgrade_sids() -> dict[str, tuple[str, ...]]:
    if not VANILLA_NPCS.exists():
        raise FileNotFoundError(VANILLA_NPCS)
    blocks = _read_blocks(VANILLA_NPCS)
    result: dict[str, tuple[str, ...]] = {}
    for sid in blocks:
        if sid in TECHNICIAN_TEMPLATE_SIDS:
            continue
        if _effective_scalar(blocks, sid, "NPCType") != "ENPCType::Technician":
            continue
        enabled = tuple(
            upgrade_sid
            for upgrade_sid, is_enabled in _effective_upgrade_entries(blocks, sid)
            if is_enabled
        )
        result[sid] = enabled
    return result


@lru_cache(maxsize=1)
def vanilla_upgrade_general_setups() -> dict[str, frozenset[str]]:
    """Invert effective Vanilla GeneralSetup upgrade arrays."""
    result: dict[str, set[str]] = {}
    for setup_sid, upgrade_sids in vanilla_general_setup_upgrades().items():
        for upgrade_sid in upgrade_sids:
            result.setdefault(upgrade_sid, set()).add(setup_sid)
    return {sid: frozenset(setups) for sid, setups in result.items()}


@lru_cache(maxsize=1)
def vanilla_technician_general_setups() -> dict[str, frozenset[str]]:
    upgrade_to_setups = vanilla_upgrade_general_setups()
    result: dict[str, frozenset[str]] = {}
    for technician_sid, upgrade_sids in vanilla_technician_upgrade_sids().items():
        setups: set[str] = set()
        for upgrade_sid in upgrade_sids:
            setups.update(upgrade_to_setups.get(upgrade_sid, ()))
        result[technician_sid] = frozenset(setups)
    return result


def technician_upgrade_assignments(model: UpgradeBuildModel) -> dict[str, list[UpgradeDefinition]]:
    """Select BPRUE upgrades only for weapons supported by each Vanilla technician."""
    support = vanilla_technician_general_setups()
    candidates = model.technician_upgrades()
    assignments: dict[str, list[UpgradeDefinition]] = {}
    for technician_sid, supported_setups in support.items():
        assignments[technician_sid] = [
            upgrade
            for upgrade in candidates
            if any(setup_sid in supported_setups for setup_sid in upgrade.general_setup_sids)
        ]
    return assignments
