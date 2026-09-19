from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from vanilla_upgrade_layout import (
    MAX_VISIBLE_HORIZONTAL_POSITION,
    available_target_parts,
    dlc_general_setup_upgrades,
    effective_modifications_for_scope,
    vanilla_general_setup_upgrades,
)

GROUP_ORDER = {
    "AR": {"Body": ["Caliber", "AdditionalCaliber", "FireControl", "Reload", "ModuleReliability"], "Barrel": ["FireRate", "ModulePrecision", "ModuleAction", "ModuleBallistics"], "Stock": ["Stock"]},
    "SMG": {"Body": ["Readiness", "Reload", "ModuleHandling"], "Barrel": ["Action", "ModuleAction", "ModuleBallistics", "ModuleRangeProfile"], "Stock": ["Stock"]},
    "SG": {"Body": ["Action", "Handling", "ModuleHandling", "ModuleReliability"], "Barrel": ["Pattern", "ModuleRangeProfile"]},
    "Pistol": {"Body": ["Handling", "ModuleHandling"], "Barrel": ["Action", "Signature", "ModulePrecision", "ModuleBallistics"]},
    "Sniper": {"Body": ["Caliber", "Marksman", "ModuleReliability"], "Barrel": ["Ballistics", "Action", "Signature", "ModulePrecision", "ModuleBallistics", "ModuleRangeProfile"], "Stock": ["Stock"]},
    "MG": {
        "Body": ["SustainedFire", "FeedSystem", "ModuleReliability"],
        "Barrel": ["BarrelConfiguration", "ModuleBallistics"],
        "Stock": ["SupportConfiguration"],
    },
}
CLASS_ORDER = ("AR", "SMG", "SG", "Pistol", "Sniper", "MG")
VERTICALS = ("Top", "Down", None)
FALLBACK_PARTS = {
    "Barrel": ("Body", "Stock", "Handguard", "PistolGrip"), "Body": ("Stock", "Handguard", "PistolGrip", "Barrel"),
    "Stock": ("Body", "PistolGrip", "Handguard", "Barrel"), "Handguard": ("Body", "Barrel", "Stock", "PistolGrip"),
    "PistolGrip": ("Body", "Stock", "Handguard", "Barrel"),
}


def _group_rank(upgrade: UpgradeDefinition) -> tuple[int, int, str, str]:
    class_rank = {name: index for index, name in enumerate(CLASS_ORDER)}; groups = GROUP_ORDER.get(upgrade.weapon_class, {}).get(upgrade.target_part, [])
    return (class_rank.get(upgrade.weapon_class, len(class_rank)), groups.index(upgrade.group) if upgrade.group in groups else len(groups), upgrade.weapon_class, upgrade.group)


def _setup_upgrades(content_pack: str | None) -> dict[str, list[str]]:
    return dlc_general_setup_upgrades(content_pack) if content_pack else vanilla_general_setup_upgrades()


def _vanilla_occupancy(setup_sid: str, content_pack: str | None) -> dict[tuple[str, int], int]:
    mods = effective_modifications_for_scope(content_pack); result = defaultdict(int)
    for sid in _setup_upgrades(content_pack).get(setup_sid, []):
        mod = mods.get(sid)
        if mod:
            target, horizontal = mod
            if 0 <= horizontal <= MAX_VISIBLE_HORIZONTAL_POSITION: result[(target, horizontal)] += 1
    return result


def _target_order(setup_sid: str, preferred: str, content_pack: str | None) -> tuple[str, ...]:
    available = available_target_parts(setup_sid, include_disabled=True, content_pack=content_pack)
    if not available: raise ValueError(f"{content_pack + '/' if content_pack else ''}{setup_sid}: no WeaponPrototype SectionSettings found")
    wanted = (preferred, *FALLBACK_PARTS.get(preferred, ())); ordered = [part for part in wanted if part in available]
    ordered.extend(part for part in available if part not in ordered); return tuple(ordered)


def _first_free_column(setup_sid, preferred, occupied_columns, content_pack):
    for target in _target_order(setup_sid, preferred, content_pack):
        for horizontal in range(MAX_VISIBLE_HORIZONTAL_POSITION + 1):
            if (target, horizontal) not in occupied_columns: return target, horizontal
    raise ValueError(f"{setup_sid}: no visible H0-H{MAX_VISIBLE_HORIZONTAL_POSITION} column left for group on {preferred}")


def _standalone_cell(setup_sid, preferred, cells, vanilla_columns, content_pack):
    targets = _target_order(setup_sid, preferred, content_pack)
    for target in targets:
        for horizontal in range(MAX_VISIBLE_HORIZONTAL_POSITION + 1):
            key = (target, horizontal)
            if key in vanilla_columns: continue
            used = cells.get(key)
            if not used: continue
            for vertical in range(len(VERTICALS)):
                if vertical not in used: return target, horizontal, vertical
    for target in targets:
        for horizontal in range(MAX_VISIBLE_HORIZONTAL_POSITION + 1):
            key = (target, horizontal)
            if key not in vanilla_columns and not cells.get(key): return target, horizontal, 0
    raise ValueError(f"{setup_sid}: no visible cell left for standalone upgrade on {preferred}")


def apply_layout_to_model(model: UpgradeBuildModel, *, content_pack: str | None = None) -> None:
    """Allocate BPRUE modules against base-game or one DLC pack's effective Vanilla layout."""
    by_setup = defaultdict(list)
    for upgrade in model.upgrades:
        if len(upgrade.general_setup_sids) != 1:
            raise ValueError(f"Layout-bearing upgrade {upgrade.sid} targets multiple GeneralSetups: {', '.join(upgrade.general_setup_sids)}. Split it into weapon-specific prototypes.")
        by_setup[upgrade.general_setup_sids[0]].append(upgrade)

    resolved_by_sid = {}
    for setup_sid, upgrades in by_setup.items():
        vanilla = _vanilla_occupancy(setup_sid, content_pack); vanilla_columns = set(vanilla); occupied_columns = set(vanilla_columns)
        cells = defaultdict(set); grouped = defaultdict(list); standalones = []; passthrough = []
        for upgrade in upgrades:
            if upgrade.standalone: standalones.append(upgrade); continue
            allowed = GROUP_ORDER.get(upgrade.weapon_class, {}).get(upgrade.target_part, [])
            if upgrade.group not in allowed: passthrough.append(upgrade); continue
            grouped[(upgrade.weapon_class, upgrade.group)].append(upgrade)

        for (_weapon_class, _group), variants in sorted(grouped.items(), key=lambda item: _group_rank(item[1][0])):
            if len(variants) > len(VERTICALS): raise ValueError(f"{setup_sid}/{variants[0].group}: {len(variants)} variants exceed 3 vertical slots")
            target, horizontal = _first_free_column(setup_sid, variants[0].target_part, occupied_columns, content_pack); occupied_columns.add((target, horizontal))
            for index, upgrade in enumerate(variants):
                cells[(target, horizontal)].add(index); resolved_by_sid[upgrade.sid] = replace(upgrade, target_part=target, horizontal_position=None if horizontal == 0 else horizontal, vertical_position=VERTICALS[index])

        for upgrade in standalones:
            prerequisite = next((resolved_by_sid.get(sid) for sid in upgrade.required_upgrade_sids if sid in resolved_by_sid), None)
            if prerequisite is not None:
                # Dependency-chain test: render the follow-up in the prerequisite's
                # column and intentionally omit VerticalPosition.
                target = prerequisite.target_part
                horizontal = prerequisite.horizontal_position or 0
                occupied_columns.add((target, horizontal))
                resolved_by_sid[upgrade.sid] = replace(
                    upgrade,
                    target_part=target,
                    horizontal_position=None if horizontal == 0 else horizontal,
                    vertical_position=None,
                )
                continue
            target, horizontal, vertical_index = _standalone_cell(setup_sid, upgrade.target_part, cells, vanilla_columns, content_pack)
            cells[(target, horizontal)].add(vertical_index); occupied_columns.add((target, horizontal)); resolved_by_sid[upgrade.sid] = replace(upgrade, target_part=target, horizontal_position=None if horizontal == 0 else horizontal, vertical_position=VERTICALS[vertical_index])
        for upgrade in passthrough: resolved_by_sid[upgrade.sid] = upgrade

    missing = [upgrade.sid for upgrade in model.upgrades if upgrade.sid not in resolved_by_sid]
    if missing: raise ValueError("Layout allocator did not resolve: " + ", ".join(missing))
    model.upgrades = [resolved_by_sid[upgrade.sid] for upgrade in model.upgrades]
