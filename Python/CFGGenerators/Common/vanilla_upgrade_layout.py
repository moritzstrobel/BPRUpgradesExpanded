from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
VANILLA_ROOT = PYTHON_ROOT / "VanillaReference"
VANILLA_UPGRADES = VANILLA_ROOT / "UpgradePrototypes.cfg"
VANILLA_GENERAL_SETUPS = VANILLA_ROOT / "WeaponGeneralSetupPrototypes.cfg"
VANILLA_WEAPONS = VANILLA_ROOT / "WeaponPrototypes.cfg"
DLC_ROOT = VANILLA_ROOT / "DLCGameData"
MAX_VISIBLE_HORIZONTAL_POSITION = 2


def _top_level_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []; current = None; depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if not line.startswith((" ", "\t")) and ": struct.begin" in stripped:
                current = [line]; depth = 1
            continue
        current.append(line)
        if "struct.begin" in stripped: depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0: blocks.append(current); current = None
    return blocks


def _sid(block: list[str]) -> str: return block[0].split(" :", 1)[0].strip()

def _refkey(block: list[str]) -> str | None:
    match = re.search(r"\{[^}]*\brefkey=([^;}]+)", block[0]); return match.group(1).strip() if match else None


def _direct_scalar(block: list[str], name: str) -> str | None:
    prefix = name + " ="; depth = 0
    for line in block[1:-1]:
        stripped = line.strip()
        if depth == 0 and stripped.startswith(prefix): return stripped.split("=", 1)[1].strip()
        if "struct.begin" in stripped: depth += 1
        if stripped == "struct.end": depth -= 1
    return None


def _direct_child(block: list[str], name: str) -> list[str] | None:
    for index, line in enumerate(block[1:-1], start=1):
        if not line.strip().startswith(name + " : struct.begin"): continue
        child = [line]; depth = 1
        for nested in block[index + 1:]:
            child.append(nested); s = nested.strip()
            if "struct.begin" in s: depth += 1
            if s == "struct.end":
                depth -= 1
                if depth == 0: return child
    return None


def _indexed_children(block: list[str] | None) -> list[list[str]]:
    if not block: return []
    result = []; i = 1
    while i < len(block) - 1:
        if re.match(r"\s*\[\d+\]\s*:\s*struct\.begin", block[i]):
            child = [block[i]]; depth = 1; i += 1
            while i < len(block) and depth:
                child.append(block[i]); s = block[i].strip()
                if "struct.begin" in s: depth += 1
                if s == "struct.end": depth -= 1
                i += 1
            result.append(child); continue
        i += 1
    return result


def _array_values(child: list[str] | None) -> list[str]:
    if not child: return []
    values = []
    for line in child[1:-1]:
        match = re.match(r"\s*(?:\[[^\]]+\]|[^=]+)\s*=\s*([A-Za-z0-9_]+)\s*$", line)
        if match and match.group(1) not in values: values.append(match.group(1))
    return values


def _read_blocks(path: Path) -> dict[str, list[str]]:
    return {_sid(block): block for block in _top_level_blocks(path.read_text(encoding="utf-8"))} if path.exists() else {}


@lru_cache(maxsize=1)
def vanilla_modifications() -> dict[str, tuple[str, int]]:
    if not VANILLA_UPGRADES.exists(): raise FileNotFoundError(VANILLA_UPGRADES)
    result = {}
    for block in _top_level_blocks(VANILLA_UPGRADES.read_text(encoding="utf-8")):
        if (_direct_scalar(block, "IsModification") or "").lower() != "true": continue
        target = _direct_scalar(block, "UpgradeTargetPart")
        if not target: continue
        raw = _direct_scalar(block, "HorizontalPosition")
        horizontal = int(raw) if raw and re.fullmatch(r"-?\d+", raw) else 0
        result[_sid(block)] = (target.rsplit("::", 1)[-1], horizontal)
    return result


@lru_cache(maxsize=1)
def _general_setup_blocks() -> dict[str, list[str]]: return _read_blocks(VANILLA_GENERAL_SETUPS)

@lru_cache(maxsize=1)
def _weapon_blocks() -> dict[str, list[str]]: return _read_blocks(VANILLA_WEAPONS)


def _inherited_array_values(blocks: dict[str, list[str]], sid: str, child_name: str, fallback: dict[str, list[str]] | None = None) -> list[str]:
    seen = set(); current = sid; fallback = fallback or {}
    while current and current not in seen:
        seen.add(current); block = blocks.get(current) or fallback.get(current)
        if not block: return []
        values = _array_values(_direct_child(block, child_name))
        if values: return values
        current = _refkey(block)
    return []


@lru_cache(maxsize=1)
def vanilla_general_setup_upgrades() -> dict[str, list[str]]:
    blocks = _general_setup_blocks(); result = {}
    for sid in blocks:
        values = _inherited_array_values(blocks, sid, "UpgradePrototypeSIDs")
        if values: result[sid] = values
    return result


@lru_cache(maxsize=None)
def dlc_general_setup_upgrades(pack: str) -> dict[str, list[str]]:
    """Effective Vanilla upgrade arrays for one DLC pack, including base-game inheritance."""
    local = _read_blocks(DLC_ROOT / pack / "WeaponData" / "WeaponGeneralSetupPrototypes.cfg")
    vanilla = _general_setup_blocks(); result = {}
    for sid in local:
        values = _inherited_array_values(local, sid, "UpgradePrototypeSIDs", vanilla)
        if values: result[sid] = values
    return result


def _sections_from_block(block: list[str]) -> dict[str, bool]:
    settings = _direct_child(block, "SectionSettings")
    if not settings: return {}
    result = {}
    for section in _indexed_children(settings):
        target = _direct_scalar(section, "UpgradeTargetPartType"); enabled = _direct_scalar(section, "SectionIsEnabled")
        if target: result[target.rsplit("::", 1)[-1]] = (enabled or "").lower() == "true"
    return result


def _inherited_weapon_sections(blocks: dict[str, list[str]], weapon_sid: str, fallback: dict[str, list[str]] | None = None) -> dict[str, bool]:
    seen = set(); current = weapon_sid; fallback = fallback or {}
    while current and current not in seen:
        seen.add(current); block = blocks.get(current) or fallback.get(current)
        if not block: return {}
        sections = _sections_from_block(block)
        if sections: return sections
        current = _refkey(block)
    return {}


@lru_cache(maxsize=1)
def weapon_sections_by_general_setup() -> dict[str, dict[str, bool]]:
    blocks = _weapon_blocks(); result = {}
    for weapon_sid, block in blocks.items():
        setup = _direct_scalar(block, "GeneralWeaponSetup")
        if setup:
            sections = _inherited_weapon_sections(blocks, weapon_sid)
            if sections: result[setup] = sections
    return result


@lru_cache(maxsize=None)
def dlc_weapon_sections_by_general_setup(pack: str) -> dict[str, dict[str, bool]]:
    """Effective SectionSettings for DLC weapons, falling back through base-game weapon inheritance."""
    local = _read_blocks(DLC_ROOT / pack / "ItemPrototypes.cfg"); vanilla = _weapon_blocks(); result = {}
    for weapon_sid, block in local.items():
        setup = _direct_scalar(block, "GeneralWeaponSetup")
        if not setup: continue
        sections = _inherited_weapon_sections(local, weapon_sid, vanilla)
        if sections: result[setup] = sections
    return result


def available_target_parts(general_setup_sid: str, include_disabled: bool = False, *, content_pack: str | None = None) -> tuple[str, ...]:
    mapping = dlc_weapon_sections_by_general_setup(content_pack) if content_pack else weapon_sections_by_general_setup()
    sections = mapping.get(general_setup_sid, {})
    return tuple(target for target, enabled in sections.items() if enabled or include_disabled)


@lru_cache(maxsize=1)
def vanilla_compaction() -> dict[str, tuple[str, int, int]]:
    modifications = vanilla_modifications(); setups = vanilla_general_setup_upgrades(); requested = defaultdict(set)
    for upgrade_sids in setups.values():
        by_target = defaultdict(list)
        for sid in upgrade_sids:
            mod = modifications.get(sid)
            if mod: by_target[mod[0]].append((sid, mod[1]))
        for target, entries in by_target.items():
            occupied = sorted({horizontal for _, horizontal in entries}); compact = {old: new for new, old in enumerate(occupied)}
            for sid, old in entries: requested[sid].add((target, compact[old]))
    moves = {}
    for sid, requests in requested.items():
        if len(requests) != 1: continue
        target, new = next(iter(requests)); original_target, old = modifications[sid]
        if target == original_target and new != old: moves[sid] = (target, old, new)
    return moves


@lru_cache(maxsize=1)
def effective_vanilla_modifications() -> dict[str, tuple[str, int]]:
    result = dict(vanilla_modifications())
    for sid, (target, _old, new) in vanilla_compaction().items(): result[sid] = (target, new)
    return result


def effective_modifications_for_scope(content_pack: str | None = None) -> dict[str, tuple[str, int]]:
    """Return modification layout as it is effective in the requested content scope.

    BaseGame uses BPRUE's safe compaction patch. DLC packs do not currently receive
    that base-game UpgradePrototype patch in their own scope, so their inherited
    Vanilla modification positions must stay at the original columns.
    """
    return vanilla_modifications() if content_pack else effective_vanilla_modifications()


def render_vanilla_compaction_patch() -> str:
    moves = vanilla_compaction(); lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// Compacts safe Vanilla IsModification=true upgrade columns for BPRUE.", "// -----------------------------------------------------------------------------", ""]
    for sid in sorted(moves):
        target, old, new = moves[sid]; lines += [f"// {target}: H{old} -> H{new}", f"{sid} : struct.begin {{bpatch}}", f"   HorizontalPosition = {new}", "struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


def modification_max_columns_for_general_setups(general_setup_sids: list[str], *, content_pack: str | None = None) -> dict[str, int]:
    modifications = effective_modifications_for_scope(content_pack); setups = dlc_general_setup_upgrades(content_pack) if content_pack else vanilla_general_setup_upgrades(); maxima = {}
    for setup_sid in general_setup_sids:
        for upgrade_sid in setups.get(setup_sid, []):
            mod = modifications.get(upgrade_sid)
            if mod:
                target, horizontal = mod; maxima[target] = max(maxima.get(target, -1), horizontal)
    return maxima


def free_visible_columns(general_setup_sid: str, target_part: str, *, content_pack: str | None = None) -> tuple[int, ...]:
    start = modification_max_columns_for_general_setups([general_setup_sid], content_pack=content_pack).get(target_part, -1) + 1
    return () if start > MAX_VISIBLE_HORIZONTAL_POSITION else tuple(range(start, MAX_VISIBLE_HORIZONTAL_POSITION + 1))


def group_columns_for_general_setups(general_setup_sids: list[str], target_part: str, groups: list[str], *, content_pack: str | None = None) -> dict[str, int]:
    start = modification_max_columns_for_general_setups(general_setup_sids, content_pack=content_pack).get(target_part, -1) + 1
    return {group: start + index for index, group in enumerate(groups)}
