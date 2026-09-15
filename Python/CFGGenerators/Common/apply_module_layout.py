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

# Some GeneralSetups participate in more than one generator/class (currently M10
# as Pistol + SMG caliber conversion). Class order makes their combined layout
# deterministic while preserving the normal per-class group order.
CLASS_ORDER = ("AR", "SMG", "SG", "Pistol", "Sniper")


def _layout_groups(model: UpgradeBuildModel) -> dict[tuple[str, str], list[tuple[str, str]]]:
    """Return ordered BPRUE groups per concrete GeneralSetup and target part.

    Columns belong to the final GeneralSetup UI table, not to a generator/class.
    Therefore groups from different weapon classes that target the same setup/part
    must be allocated together instead of independently starting at the same column.
    """
    found: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)

    for upgrade in model.upgrades:
        allowed = GROUP_ORDER.get(upgrade.weapon_class, {}).get(upgrade.target_part, [])
        if upgrade.group not in allowed:
            continue
        for setup_sid in upgrade.general_setup_sids:
            found[(setup_sid, upgrade.target_part)].add((upgrade.weapon_class, upgrade.group))

    ordered: dict[tuple[str, str], list[tuple[str, str]]] = {}
    class_rank = {weapon_class: index for index, weapon_class in enumerate(CLASS_ORDER)}

    for key, groups in found.items():
        _, target_part = key

        def sort_key(item: tuple[str, str]) -> tuple[int, int, str, str]:
            weapon_class, group = item
            class_groups = GROUP_ORDER[weapon_class][target_part]
            return (
                class_rank.get(weapon_class, len(class_rank)),
                class_groups.index(group),
                weapon_class,
                group,
            )

        ordered[key] = sorted(groups, key=sort_key)

    return ordered


def apply_layout_to_model(model: UpgradeBuildModel) -> None:
    """Resolve final module coordinates before CFG rendering.

    For each concrete GeneralSetup/target part, every BPRUE group that is actually
    present consumes exactly one column, even when multiple class generators feed
    the same setup. The first group starts directly after the last Vanilla
    IsModification=true column. Variants use Top, Down, then omit VerticalPosition.
    """
    layout_groups = _layout_groups(model)
    column_cache: dict[tuple[str, str], dict[tuple[str, str], int]] = {}
    variant_counts: dict[tuple[str, str, str, int], int] = {}
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
        cache_key = (setup_sid, upgrade.target_part)
        columns = column_cache.get(cache_key)
        if columns is None:
            groups = layout_groups[cache_key]
            # Reuse the Vanilla-aware start-column helper with synthetic unique
            # names, then map those columns back to (weapon_class, group).
            synthetic_groups = [f"{weapon_class}:{group}" for weapon_class, group in groups]
            synthetic_columns = group_columns_for_general_setups(
                [setup_sid],
                upgrade.target_part,
                synthetic_groups,
            )
            columns = {
                group_key: synthetic_columns[synthetic]
                for group_key, synthetic in zip(groups, synthetic_groups)
            }
            column_cache[cache_key] = columns

        group_key = (upgrade.weapon_class, upgrade.group)
        column = columns[group_key]
        variant_key = (setup_sid, upgrade.weapon_class, upgrade.group, column)
        index = variant_counts.get(variant_key, 0)
        vertical = "Top" if index == 0 else "Down" if index == 1 else None
        variant_counts[variant_key] = index + 1
        resolved.append(replace(
            upgrade,
            horizontal_position=None if column == 0 else column,
            vertical_position=vertical,
        ))

    model.upgrades = resolved
