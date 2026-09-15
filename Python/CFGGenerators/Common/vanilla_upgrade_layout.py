from __future__ import annotations

import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
VANILLA_UPGRADES = PYTHON_ROOT / "VanillaReference" / "UpgradePrototypes.cfg"
VANILLA_GENERAL_SETUPS = PYTHON_ROOT / "VanillaReference" / "WeaponGeneralSetupPrototypes.cfg"


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
    i = 1
    while i < len(block) - 1:
        line = block[i]
        stripped = line.strip()
        if line.startswith("   ") and not line.startswith("      ") and stripped.startswith(name + " : struct.begin"):
            child = [line]
            depth = 1
            i += 1
            while i < len(block) - 1 and depth:
                child.append(block[i])
                s = block[i].strip()
                if "struct.begin" in s:
                    depth += 1
                if s == "struct.end":
                    depth -= 1
                i += 1
            return child
        i += 1
    return None


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
    """Return vanilla modification SID -> (target part, horizontal column)."""
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
def vanilla_general_setup_upgrades() -> dict[str, list[str]]:
    """Return GeneralSetup SID -> its vanilla UpgradePrototypeSIDs."""
    if not VANILLA_GENERAL_SETUPS.exists():
        raise FileNotFoundError(VANILLA_GENERAL_SETUPS)

    result: dict[str, list[str]] = {}
    for block in _top_level_blocks(VANILLA_GENERAL_SETUPS.read_text(encoding="utf-8")):
        values = _array_values(_direct_child(block, "UpgradePrototypeSIDs"))
        if values:
            result[_sid(block)] = values
    return result


@lru_cache(maxsize=1)
def vanilla_compaction() -> dict[str, tuple[str, int, int]]:
    """Return safe Vanilla column moves as SID -> (target, old H, new H).

    Each GeneralSetup is compacted independently by mapping its occupied modification
    columns to 0..N while preserving column order. Upgrade prototypes are global, so
    a move is emitted only when every GeneralSetup using that SID requests the same
    target/new column. Ambiguous shared prototypes are deliberately left untouched.
    """
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
    """Vanilla modification layout after applying the generated compaction patch."""
    result = dict(vanilla_modifications())
    for sid, (target, _old, new) in vanilla_compaction().items():
        result[sid] = (target, new)
    return result


def render_vanilla_compaction_patch() -> str:
    moves = vanilla_compaction()
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Compacts safe Vanilla IsModification=true upgrade columns for BPRUE.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for sid in sorted(moves):
        target, old, new = moves[sid]
        lines += [
            f"// {target}: H{old} -> H{new}",
            f"{sid} : struct.begin {{bpatch}}",
            f"   HorizontalPosition = {new}",
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def modification_max_columns_for_general_setups(general_setup_sids: list[str]) -> dict[str, int]:
    """Max effective Vanilla modification column per target part for concrete weapons."""
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


def group_columns_for_general_setups(
    general_setup_sids: list[str], target_part: str, groups: list[str]
) -> dict[str, int]:
    maxima = modification_max_columns_for_general_setups(general_setup_sids)
    start = maxima.get(target_part, -1) + 1
    return {group: start + index for index, group in enumerate(groups)}
