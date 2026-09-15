from __future__ import annotations

import json
from pathlib import Path

from vanilla_upgrade_layout import group_columns_for_general_setups

SCRIPT_DIR = Path(__file__).resolve().parent

CONFIG_FILES = {
    "AR": SCRIPT_DIR / "assault_rifles_upgrades.json",
    "SMG": SCRIPT_DIR / "smg_upgrades.json",
    "SG": SCRIPT_DIR / "shotgun_upgrades.json",
    "Pistol": SCRIPT_DIR / "pistol_upgrades.json",
    "Sniper": SCRIPT_DIR / "sniper_upgrades.json",
}

# Every BPRUE module group owns one column inside its target part. The actual
# placement is calculated from VanillaReference and applied by the final upgrade
# merger while the generated class sections are already in memory.
GROUP_ORDER = {
    "AR": {
        "Body": ["Caliber", "FireControl", "Reload"],
        "Barrel": ["FireRate"],
        "Stock": ["Stock"],
    },
    "SMG": {
        "Body": ["Readiness", "Reload", "Caliber", "Conversion"],
        "Barrel": ["Action"],
    },
    "SG": {
        "Body": ["Action", "Handling"],
        "Barrel": ["Pattern"],
    },
    "Pistol": {
        "Body": ["Handling"],
        "Barrel": ["Action", "Signature"],
    },
    "Sniper": {
        "Body": ["Marksman"],
        "Barrel": ["Ballistics", "Action", "Signature"],
    },
}


def load_configs() -> dict[str, dict]:
    return {
        weapon_class: json.loads(path.read_text(encoding="utf-8"))
        for weapon_class, path in CONFIG_FILES.items()
    }


def family_records(configs: dict[str, dict], weapon_class: str) -> list[tuple[str, str]]:
    """Return (prototype prefix, GeneralSetup SID) for a weapon class."""
    config = configs[weapon_class]
    records: list[tuple[str, str]] = []

    for family in config.get("families", {}).values():
        prefix = family.get("prototype_prefix")
        general_setup = family.get("general_setup_sid") or family.get("weapon_sid")
        if prefix and general_setup and (prefix, general_setup) not in records:
            records.append((prefix, general_setup))

    # M10 participates in the SMG caliber system although its normal family is
    # owned by the pistol generator.
    if weapon_class == "SMG":
        for family in config.get("caliber_families", {}).values():
            prefix = family.get("prototype_prefix")
            general_setup = family.get("general_setup_sid")
            if prefix and general_setup and (prefix, general_setup) not in records:
                records.append((prefix, general_setup))
    return records


def class_general_setups(configs: dict[str, dict], weapon_class: str) -> list[str]:
    return list(dict.fromkeys(setup for _, setup in family_records(configs, weapon_class)))


def classify(sid: str) -> tuple[str, str] | None:
    if "_Upgrade_BPRUE_Sniper_" in sid:
        return "Sniper", sid.split("_Upgrade_BPRUE_Sniper_", 1)[1].split("_", 1)[0]
    if "_Upgrade_BPRUE_Pistol_" in sid:
        return "Pistol", sid.split("_Upgrade_BPRUE_Pistol_", 1)[1].split("_", 1)[0]
    if "_Upgrade_BPRUE_SG_" in sid:
        return "SG", sid.split("_Upgrade_BPRUE_SG_", 1)[1].split("_", 1)[0]
    if sid.startswith("BPRUE_SMG_Upgrade_"):
        return "SMG", sid.split("BPRUE_SMG_Upgrade_", 1)[1].split("_", 1)[0]
    if "_Upgrade_BPRUE_Caliber_" in sid:
        return "AUTO_CALIBER", "Caliber"
    if "_Upgrade_BPRUE_PistolConversion" in sid:
        return "SMG", "Conversion"
    for token, group in (
        ("_Upgrade_BPRUE_FireControl_", "FireControl"),
        ("_Upgrade_BPRUE_FireRate_", "FireRate"),
        ("_Upgrade_BPRUE_Reload_", "Reload"),
        ("_Upgrade_BPRUE_Stock_", "Stock"),
    ):
        if token in sid:
            return "AR", group
    return None


def file_class_hint(path: Path) -> str:
    if "SMG" in path.name:
        return "SMG"
    if "Shotgun" in path.name:
        return "SG"
    if "Pistol" in path.name:
        return "Pistol"
    if "Sniper" in path.name:
        return "Sniper"
    return "AR"


def relevant_general_setups(sid: str, weapon_class: str, configs: dict[str, dict]) -> list[str]:
    """Resolve concrete families using an upgrade; also validates SID ownership."""
    records = family_records(configs, weapon_class)

    if sid.startswith("BPRUE_SMG_Upgrade_"):
        normal_families = configs["SMG"].get("families", {}).values()
        return list(dict.fromkeys(
            family.get("general_setup_sid") or family.get("weapon_sid")
            for family in normal_families
            if family.get("general_setup_sid") or family.get("weapon_sid")
        ))

    matches = [
        general_setup
        for prefix, general_setup in sorted(records, key=lambda item: len(item[0]), reverse=True)
        if sid.startswith(prefix + "_")
    ]
    if matches:
        return list(dict.fromkeys(matches))

    raise ValueError(f"Cannot resolve BPRUE upgrade {sid} to a {weapon_class} GeneralSetup family")


def class_columns(configs: dict[str, dict]) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = {}
    for weapon_class, targets in GROUP_ORDER.items():
        setups = class_general_setups(configs, weapon_class)
        result[weapon_class] = {
            target: group_columns_for_general_setups(setups, target, groups)
            for target, groups in targets.items()
        }
    return result


def patch_block(
    block: list[str],
    hint: str,
    configs: dict[str, dict],
    columns: dict[str, dict[str, dict[str, int]]],
) -> tuple[list[str], tuple[str, str, int, tuple[str, ...]] | None]:
    """Apply the calculated column to one generated top-level upgrade block."""
    sid = block[0].split(" :", 1)[0].strip()
    classified = classify(sid)
    if not classified:
        return block, None

    weapon_class, group = classified
    if weapon_class == "AUTO_CALIBER":
        weapon_class = hint

    target = None
    horizontal_index = None
    for i, line in enumerate(block):
        stripped = line.strip()
        if stripped.startswith("UpgradeTargetPart ="):
            target = stripped.rsplit("::", 1)[-1]
        elif stripped.startswith("HorizontalPosition ="):
            horizontal_index = i

    if not target or target not in GROUP_ORDER.get(weapon_class, {}):
        return block, None
    if group not in GROUP_ORDER[weapon_class][target]:
        return block, None

    setups = relevant_general_setups(sid, weapon_class, configs)
    column = columns[weapon_class][target][group]
    new_line = f"   HorizontalPosition = {column}"

    if horizontal_index is not None:
        block[horizontal_index] = new_line
    else:
        insert_at = next(
            (i for i, line in enumerate(block) if line.strip().startswith("VerticalPosition =")),
            len(block) - 1,
        )
        block.insert(insert_at, new_line)

    return block, (target, group, column, tuple(setups))
