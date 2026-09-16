from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
VANILLA_UPGRADES = PYTHON_ROOT / "VanillaReference" / "UpgradePrototypes.cfg"
VANILLA_GENERAL_SETUPS = PYTHON_ROOT / "VanillaReference" / "WeaponGeneralSetupPrototypes.cfg"
VANILLA_WEAPONS = PYTHON_ROOT / "VanillaReference" / "WeaponPrototypes.cfg"
MAX_VISIBLE_HORIZONTAL_POSITION = 2


def _top_level_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if not line.startswith((" ", "\t")) and ": struct.begin" in stripped:
                current = [line]
                depth = 1
            continue
        current.append(line)
        if "struct.begin" in stripped:
            depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0:
                blocks.append(current)
                current = None
    return blocks


def _sid(block: list[str]) -> str:
    return block[0].split(" :", 1)[0].strip()


def _refkey(block: list[str]) -> str | None:
    match = re.search(r"\{[^}]*\brefkey=([^;}]+)", block[0])
    return match.group(1).strip() if match else None


def _direct_scalar(block: list[str], name: str) -> str | None:
    prefix = name + " ="
    depth = 0
    for line in block[1:-1]:
        stripped = line.strip()
        if depth == 0 and stripped.startswith(prefix):
            return stripped.split("=", 1)[1].strip()
        if "struct.begin" in stripped:
            depth += 1
        if stripped == "struct.end":
            depth -= 1
    return None


def _direct_child(block: list[str], name: str) -> list[str] | None:
    """Find a named child struct without assuming a particular indentation width."""
    for index, line in enumerate(block[1:-1], start=1):
        stripped = line.strip()
        if not stripped.startswith(name + " : struct.begin"):
            continue
        child = [line]
        depth = 1
        for nested in block[index + 1:]:
            child.append(nested)
            nested_stripped = nested.strip()
            if "struct.begin" in nested_stripped:
                depth += 1
            if nested_stripped == "struct.end":
                depth -= 1
                if depth == 0:
                    return child
    return None


def _indexed_children(block: list[str] | None) -> list[list[str]]:
    if not block:
        return []
    result: list[list[str]] = []
    i = 1
    while i < len(block) - 1:
        if re.match(r"\s*\[\d+\]\s*:\s*struct\.begin", block[i]):
            child = [block[i]]
            depth = 1
            i += 1
            while i < len(block) and depth:
                child.append(block[i])
                stripped = block[i].strip()
                if "struct.begin" in stripped:
                    depth += 1
                if stripped == "struct.end":
                    depth -= 1
                i += 1
            result.append(child)
            continue
        i += 1
    return result


def _array_values(child: list[str] | None) -> list[str]:
    if not child:
        return []
    values: list[str] = []
    for line in child[1:-1]:
        match = re.match(r"\s*(?:\[[^\]]+\]|[^=]+)\s*=\s*([A-Za-z0-9_]+)\s*$", line)
        if match and match.group(1) not in values:
            values.append(match.group(1))
    return values


@lru_cache(maxsize=1)
def vanilla_modifications() -> dict[str, tuple[str, int]]:
    if not VANILLA_UPGRADES.exists():
        raise FileNotFoundError(VANILLA_UPGRADES)
    result: dict[str, tuple[str, int]] = {}
    for block in _top_level_blocks(VANILLA_UPGRADES.read_text(encoding="utf-8")):
        if (_direct_scalar(block, "IsModification") or "").lower() != "true":
            continue
        target = _direct_scalar(block, "UpgradeTargetPart")
        if not target:
            continue
        raw_horizontal = _direct_scalar(block, "HorizontalPosition")
        horizontal = int(raw_horizontal) if raw_horizontal and re.fullmatch(r"-?\d+", raw_horizontal) else 0
        result[_sid(block)] = (target.rsplit("::", 1)[-1], horizontal)
    return result


@lru_cache(maxsize=1)
def _general_setup_blocks() -> dict[str, list[str]]:
    if not VANILLA_GENERAL_SETUPS.exists():
        raise FileNotFoundError(VANILLA_GENERAL_SETUPS)
    return {_sid(block): block for block in _top_level_blocks(VANILLA_GENERAL_SETUPS.read_text(encoding="utf-8"))}


def _inherited_array_values(blocks: dict[str, list[str]], sid: str, child_name: str) -> list[str]:
    """Resolve a direct array through the Vanilla refkey chain.

    Unique GeneralSetups commonly inherit the base weapon's upgrade array instead
    of declaring their own. BPRUE must account for that inherited Vanilla occupancy
    when allocating new columns for the Unique.
    """
    seen: set[str] = set()
    current = sid
    while current and current not in seen:
        seen.add(current)
        block = blocks.get(current)
        if not block:
            return []
        values = _array_values(_direct_child(block, child_name))
        if values:
            return values
        current = _refkey(block)
    return []


@lru_cache(maxsize=1)
def vanilla_general_setup_upgrades() -> dict[str, list[str]]:
    blocks = _general_setup_blocks()
    result: dict[str, list[str]] = {}
    for sid in blocks:
        values = _inherited_array_values(blocks, sid, "UpgradePrototypeSIDs")
        if values:
            result[sid] = values
    return result


@lru_cache(maxsize=1)
def _weapon_blocks() -> dict[str, list[str]]:
    if not VANILLA_WEAPONS.exists():
        raise FileNotFoundError(VANILLA_WEAPONS)
    return {_sid(block): block for block in _top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8"))}


def _sections_from_block(block: list[str]) -> dict[str, bool]:
    settings = _direct_child(block, "SectionSettings")
    if not settings:
        return {}
    sections: dict[str, bool] = {}
    for section in _indexed_children(settings):
        target = _direct_scalar(section, "UpgradeTargetPartType")
        enabled = _direct_scalar(section, "SectionIsEnabled")
        if target:
            sections[target.rsplit("::", 1)[-1]] = (enabled or "").lower() == "true"
    return sections


def _inherited_weapon_sections(blocks: dict[str, list[str]], weapon_sid: str) -> dict[str, bool]:
    seen: set[str] = set()
    current = weapon_sid
    while current and current not in seen:
        seen.add(current)
        block = blocks.get(current)
        if not block:
            return {}
        sections = _sections_from_block(block)
        if sections:
            return sections
        current = _refkey(block)
    return {}


@lru_cache(maxsize=1)
def weapon_sections_by_general_setup() -> dict[str, dict[str, bool]]:
    """Map GeneralSetup SIDs to effective WeaponPrototype SectionSettings.

    A Unique may point at its own GeneralSetup while inheriting SectionSettings
    from a base WeaponPrototype. Resolve the weapon refkey chain so the layout
    allocator sees the same target parts that the Unique effectively has in game.
    """
    blocks = _weapon_blocks()
    result: dict[str, dict[str, bool]] = {}
    for weapon_sid, block in blocks.items():
        general_setup = _direct_scalar(block, "GeneralWeaponSetup")
        if not general_setup:
            continue
        sections = _inherited_weapon_sections(blocks, weapon_sid)
        if sections:
            result[general_setup] = sections
    return result


def available_target_parts(general_setup_sid: str, include_disabled: bool = False) -> tuple[str, ...]:
    sections = weapon_sections_by_general_setup().get(general_setup_sid, {})
    return tuple(target for target, enabled in sections.items() if enabled or include_disabled)


@lru_cache(maxsize=1)
def vanilla_compaction() -> dict[str, tuple[str, int, int]]:
    modifications = vanilla_modifications()
    setups = vanilla_general_setup_upgrades()
    requested: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for upgrade_sids in setups.values():
        by_target: dict[str, list[tuple[str, int]]] = defaultdict(list)
        for sid in upgrade_sids:
            modification = modifications.get(sid)
            if modification:
                target, horizontal = modification
                by_target[target].append((sid, horizontal))
        for target, entries in by_target.items():
            occupied = sorted({horizontal for _, horizontal in entries})
            compact = {old: new for new, old in enumerate(occupied)}
            for sid, old in entries:
                requested[sid].add((target, compact[old]))
    moves: dict[str, tuple[str, int, int]] = {}
    for sid, requests in requested.items():
        if len(requests) != 1:
            continue
        target, new = next(iter(requests))
        original_target, old = modifications[sid]
        if target == original_target and new != old:
            moves[sid] = (target, old, new)
    return moves


@lru_cache(maxsize=1)
def effective_vanilla_modifications() -> dict[str, tuple[str, int]]:
    result = dict(vanilla_modifications())
    for sid, (target, _old, new) in vanilla_compaction().items():
        result[sid] = (target, new)
    return result


def render_vanilla_compaction_patch() -> str:
    moves = vanilla_compaction()
    lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// Compacts safe Vanilla IsModification=true upgrade columns for BPRUE.", "// -----------------------------------------------------------------------------", ""]
    for sid in sorted(moves):
        target, old, new = moves[sid]
        lines += [f"// {target}: H{old} -> H{new}", f"{sid} : struct.begin {{bpatch}}", f"   HorizontalPosition = {new}", "struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


def modification_max_columns_for_general_setups(general_setup_sids: list[str]) -> dict[str, int]:
    modifications = effective_vanilla_modifications()
    setup_upgrades = vanilla_general_setup_upgrades()
    maxima: dict[str, int] = {}
    for general_setup_sid in general_setup_sids:
        for upgrade_sid in setup_upgrades.get(general_setup_sid, []):
            modification = modifications.get(upgrade_sid)
            if not modification:
                continue
            target, horizontal = modification
            maxima[target] = max(maxima.get(target, -1), horizontal)
    return maxima


def free_visible_columns(general_setup_sid: str, target_part: str) -> tuple[int, ...]:
    maxima = modification_max_columns_for_general_setups([general_setup_sid])
    start = maxima.get(target_part, -1) + 1
    if start > MAX_VISIBLE_HORIZONTAL_POSITION:
        return ()
    return tuple(range(start, MAX_VISIBLE_HORIZONTAL_POSITION + 1))


def group_columns_for_general_setups(general_setup_sids: list[str], target_part: str, groups: list[str]) -> dict[str, int]:
    maxima = modification_max_columns_for_general_setups(general_setup_sids)
    start = maxima.get(target_part, -1) + 1
    return {group: start + index for index, group in enumerate(groups)}
