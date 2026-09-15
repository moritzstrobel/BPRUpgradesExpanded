from __future__ import annotations

from dataclasses import replace

from upgrade_build_model import UpgradeBuildModel
from vanilla_upgrade_layout import group_columns_for_general_setups


GROUP_ORDER = {
    "AR": {"Body": ["Caliber", "FireControl", "Reload"], "Barrel": ["FireRate"], "Stock": ["Stock"]},
    "SMG": {"Body": ["Readiness", "Reload", "Caliber", "Conversion"], "Barrel": ["Action"]},
    "SG": {"Body": ["Action", "Handling"], "Barrel": ["Pattern"]},
    "Pistol": {"Body": ["Handling"], "Barrel": ["Action", "Signature"]},
    "Sniper": {"Body": ["Marksman"], "Barrel": ["Ballistics", "Action", "Signature"]},
}


def columns_for_upgrade(upgrade) -> dict[str, int]:
    """Resolve group columns relative to this upgrade's concrete weapon setups.

    Vanilla modification occupancy differs per GeneralSetup. Using every setup of
    a weapon class here would make a weapon inherit the highest occupied column of
    an unrelated weapon and introduce artificial gaps before its BPRUE modules.
    """
    groups = GROUP_ORDER.get(upgrade.weapon_class, {}).get(upgrade.target_part, [])
    return group_columns_for_general_setups(
        list(upgrade.general_setup_sids),
        upgrade.target_part,
        groups,
    )


def apply_layout_to_model(model: UpgradeBuildModel) -> None:
    """Resolve final module coordinates before CFG rendering.

    Each upgrade group starts directly after the last Vanilla IsModification=true
    column of the concrete GeneralSetup(s) that receive that upgrade. Variants
    sharing one weapon/group/column use Vanilla's Top/Down pattern; a third variant
    intentionally omits VerticalPosition.
    """
    column_cache: dict[tuple[str, str, tuple[str, ...]], dict[str, int]] = {}
    variant_counts: dict[tuple[str, str, int, tuple[str, ...]], int] = {}
    resolved = []

    for upgrade in model.upgrades:
        class_layout = GROUP_ORDER.get(upgrade.weapon_class, {})
        groups = class_layout.get(upgrade.target_part, [])
        if upgrade.group not in groups:
            resolved.append(upgrade)
            continue

        setup_sids = tuple(upgrade.general_setup_sids)
        cache_key = (upgrade.weapon_class, upgrade.target_part, setup_sids)
        columns = column_cache.get(cache_key)
        if columns is None:
            columns = columns_for_upgrade(upgrade)
            column_cache[cache_key] = columns

        column = columns[upgrade.group]
        key = (upgrade.target_part, upgrade.group, column, setup_sids)
        index = variant_counts.get(key, 0)
        vertical = "Top" if index == 0 else "Down" if index == 1 else None
        variant_counts[key] = index + 1
        resolved.append(replace(
            upgrade,
            horizontal_position=None if column == 0 else column,
            vertical_position=vertical,
        ))

    model.upgrades = resolved
