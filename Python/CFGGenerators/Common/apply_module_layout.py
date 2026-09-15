from __future__ import annotations

from collections import defaultdict
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


def _present_groups(model: UpgradeBuildModel) -> dict[tuple[str, str, str], list[str]]:
    """Return ordered groups that actually exist for each setup/class/target.

    GROUP_ORDER defines ordering only. It must not reserve columns for groups that
    are absent from a concrete weapon, otherwise artificial holes are introduced.
    """
    found: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for upgrade in model.upgrades:
        allowed = GROUP_ORDER.get(upgrade.weapon_class, {}).get(upgrade.target_part, [])
        if upgrade.group not in allowed:
            continue
        for setup_sid in upgrade.general_setup_sids:
            found[(setup_sid, upgrade.weapon_class, upgrade.target_part)].add(upgrade.group)

    ordered: dict[tuple[str, str, str], list[str]] = {}
    for key, groups in found.items():
        _, weapon_class, target_part = key
        ordered[key] = [
            group
            for group in GROUP_ORDER[weapon_class][target_part]
            if group in groups
        ]
    return ordered


def apply_layout_to_model(model: UpgradeBuildModel) -> None:
    """Resolve final module coordinates before CFG rendering.

    For each concrete GeneralSetup/class/target, only groups that are actually
    present consume columns. The first present group starts directly after the last
    Vanilla IsModification=true column. Variants in one group use Top, Down, then
    omit VerticalPosition for any further alternatives.
    """
    present_groups = _present_groups(model)
    column_cache: dict[tuple[str, str, str], dict[str, int]] = {}
    variant_counts: dict[tuple[str, str, int, str], int] = {}
    resolved = []

    for upgrade in model.upgrades:
        allowed = GROUP_ORDER.get(upgrade.weapon_class, {}).get(upgrade.target_part, [])
        if upgrade.group not in allowed:
            resolved.append(upgrade)
            continue

        setup_sids = tuple(upgrade.general_setup_sids)
        if len(setup_sids) != 1:
            raise ValueError(
                f"Layout-bearing upgrade {upgrade.sid} targets multiple GeneralSetups: "
                f"{', '.join(setup_sids)}. Split it into weapon-specific prototypes."
            )

        setup_sid = setup_sids[0]
        cache_key = (setup_sid, upgrade.weapon_class, upgrade.target_part)
        columns = column_cache.get(cache_key)
        if columns is None:
            groups = present_groups[cache_key]
            columns = group_columns_for_general_setups(
                [setup_sid],
                upgrade.target_part,
                groups,
            )
            column_cache[cache_key] = columns

        column = columns[upgrade.group]
        variant_key = (setup_sid, upgrade.group, column, upgrade.weapon_class)
        index = variant_counts.get(variant_key, 0)
        vertical = "Top" if index == 0 else "Down" if index == 1 else None
        variant_counts[variant_key] = index + 1
        resolved.append(replace(
            upgrade,
            horizontal_position=None if column == 0 else column,
            vertical_position=vertical,
        ))

    model.upgrades = resolved
