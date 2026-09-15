from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel
from vanilla_upgrade_layout import group_columns_for_general_setups

SCRIPT_DIR = Path(__file__).resolve().parent

CONFIG_FILES = {
    "AR": SCRIPT_DIR / "assault_rifles_upgrades.json",
    "SMG": SCRIPT_DIR / "smg_upgrades.json",
    "SG": SCRIPT_DIR / "shotgun_upgrades.json",
    "Pistol": SCRIPT_DIR / "pistol_upgrades.json",
    "Sniper": SCRIPT_DIR / "sniper_upgrades.json",
}

GROUP_ORDER = {
    "AR": {"Body": ["Caliber", "FireControl", "Reload"], "Barrel": ["FireRate"], "Stock": ["Stock"]},
    "SMG": {"Body": ["Readiness", "Reload", "Caliber", "Conversion"], "Barrel": ["Action"]},
    "SG": {"Body": ["Action", "Handling"], "Barrel": ["Pattern"]},
    "Pistol": {"Body": ["Handling"], "Barrel": ["Action", "Signature"]},
    "Sniper": {"Body": ["Marksman"], "Barrel": ["Ballistics", "Action", "Signature"]},
}


def load_configs() -> dict[str, dict]:
    return {weapon_class: json.loads(path.read_text(encoding="utf-8")) for weapon_class, path in CONFIG_FILES.items()}


def family_records(configs: dict[str, dict], weapon_class: str) -> list[tuple[str, str]]:
    config = configs[weapon_class]
    records: list[tuple[str, str]] = []
    for family in config.get("families", {}).values():
        prefix = family.get("prototype_prefix")
        general_setup = family.get("general_setup_sid") or family.get("weapon_sid")
        if prefix and general_setup and (prefix, general_setup) not in records:
            records.append((prefix, general_setup))
    if weapon_class == "SMG":
        for family in config.get("caliber_families", {}).values():
            prefix = family.get("prototype_prefix")
            general_setup = family.get("general_setup_sid")
            if prefix and general_setup and (prefix, general_setup) not in records:
                records.append((prefix, general_setup))
    return records


def class_general_setups(configs: dict[str, dict], weapon_class: str) -> list[str]:
    return list(dict.fromkeys(setup for _, setup in family_records(configs, weapon_class)))


def class_columns(configs: dict[str, dict]) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {}
    for weapon_class, targets in GROUP_ORDER.items():
        setups = class_general_setups(configs, weapon_class)
        result[weapon_class] = {
            target: group_columns_for_general_setups(setups, target, groups)
            for target, groups in targets.items()
        }
    return result


def apply_layout_to_model(model: UpgradeBuildModel) -> None:
    """Resolve final module coordinates before CFG rendering.

    Layout is now part of the in-memory build graph. No generated CFG is parsed or
    rewritten afterwards. Variants sharing one weapon/group/column use Vanilla's
    Top/Down pattern; a third variant intentionally omits VerticalPosition.
    """
    columns = class_columns(load_configs())
    variant_counts: dict[tuple[str, str, int, tuple[str, ...]], int] = {}
    resolved = []

    for upgrade in model.upgrades:
        class_layout = GROUP_ORDER.get(upgrade.weapon_class, {})
        groups = class_layout.get(upgrade.target_part, [])
        if upgrade.group not in groups:
            resolved.append(upgrade)
            continue

        column = columns[upgrade.weapon_class][upgrade.target_part][upgrade.group]
        key = (upgrade.target_part, upgrade.group, column, tuple(upgrade.general_setup_sids))
        index = variant_counts.get(key, 0)
        vertical = "Top" if index == 0 else "Down" if index == 1 else None
        variant_counts[key] = index + 1
        resolved.append(replace(
            upgrade,
            horizontal_position=None if column == 0 else column,
            vertical_position=vertical,
        ))

    model.upgrades = resolved
