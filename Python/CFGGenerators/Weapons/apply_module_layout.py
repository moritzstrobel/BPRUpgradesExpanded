from __future__ import annotations

import json
from pathlib import Path

from vanilla_upgrade_layout import (
    group_columns_for_general_setups,
    modification_max_columns_for_general_setups,
)

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
UPGRADE_DIR = CONTENT_ROOT / "GameLite" / "ModGameData" / "BPRUpgradesExpanded" / "UpgradePrototypes"

FILES = [
    UPGRADE_DIR / "BPRUE_UpgradePrototypes.cfg",
    UPGRADE_DIR / "BPRUE_SMGUpgradePrototypes.cfg",
    UPGRADE_DIR / "BPRUE_ShotgunUpgradePrototypes.cfg",
    UPGRADE_DIR / "BPRUE_PistolUpgradePrototypes.cfg",
    UPGRADE_DIR / "BPRUE_SniperUpgradePrototypes.cfg",
]

CONFIG_FILES = {
    "AR": SCRIPT_DIR / "assault_rifles_upgrades.json",
    "SMG": SCRIPT_DIR / "smg_upgrades.json",
    "SG": SCRIPT_DIR / "shotgun_upgrades.json",
    "Pistol": SCRIPT_DIR / "pistol_upgrades.json",
    "Sniper": SCRIPT_DIR / "sniper_upgrades.json",
}

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

    # SMG caliber_families also contains M10, which is intentionally shared with
    # the pistol generator and is not part of the normal SMG families map.
    if weapon_class == "SMG":
        for family in config.get("caliber_families", {}).values():
            prefix = family.get("prototype_prefix")
            general_setup = family.get("general_setup_sid")
            if prefix and general_setup and (prefix, general_setup) not in records:
                records.append((prefix, general_setup))
    return records


def classify(sid: str) -> tuple[str, str] | None:
    if "_Upgrade_BPRUE_Sniper_" in sid:
        tail = sid.split("_Upgrade_BPRUE_Sniper_", 1)[1]
        return "Sniper", tail.split("_", 1)[0]
    if "_Upgrade_BPRUE_Pistol_" in sid:
        tail = sid.split("_Upgrade_BPRUE_Pistol_", 1)[1]
        return "Pistol", tail.split("_", 1)[0]
    if "_Upgrade_BPRUE_SG_" in sid:
        tail = sid.split("_Upgrade_BPRUE_SG_", 1)[1]
        return "SG", tail.split("_", 1)[0]
    if sid.startswith("BPRUE_SMG_Upgrade_"):
        tail = sid.split("BPRUE_SMG_Upgrade_", 1)[1]
        return "SMG", tail.split("_", 1)[0]
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


def relevant_general_setups(
    sid: str, weapon_class: str, configs: dict[str, dict]
) -> list[str]:
    records = family_records(configs, weapon_class)

    # Shared SMG module prototypes have no weapon prefix and are intentionally
    # reused by every SMG. Their position therefore has to be safe for the SMG
    # families only, not for every Body/Barrel modification in the whole game.
    if sid.startswith("BPRUE_SMG_Upgrade_"):
        normal_families = configs["SMG"].get("families", {}).values()
        return list(dict.fromkeys(
            family.get("general_setup_sid") or family.get("weapon_sid")
            for family in normal_families
            if family.get("general_setup_sid") or family.get("weapon_sid")
        ))

    # All other generated module SIDs contain their family prototype prefix.
    # Longest-prefix-first avoids accidental short-prefix matches.
    matches = [
        general_setup
        for prefix, general_setup in sorted(records, key=lambda item: len(item[0]), reverse=True)
        if sid.startswith(prefix + "_")
    ]
    if matches:
        return list(dict.fromkeys(matches))

    # Fail loudly instead of silently falling back to a global layout again.
    raise ValueError(f"Cannot resolve BPRUE upgrade {sid} to a {weapon_class} GeneralSetup family")


def patch_block(
    block: list[str], hint: str, configs: dict[str, dict]
) -> tuple[list[str], tuple[str, str, int, tuple[str, ...]] | None]:
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
    groups = GROUP_ORDER[weapon_class][target]
    if group not in groups:
        return block, None

    setups = relevant_general_setups(sid, weapon_class, configs)
    column = group_columns_for_general_setups(setups, target, groups)[group]

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


def process(path: Path, configs: dict[str, dict]) -> list[tuple[str, str, int, tuple[str, ...]]]:
    if not path.exists():
        raise FileNotFoundError(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    placements: list[tuple[str, str, int, tuple[str, ...]]] = []
    i = 0
    hint = file_class_hint(path)
    while i < len(lines):
        line = lines[i]
        if not line.startswith((" ", "\t")) and ": struct.begin" in line:
            block = [line]
            depth = 1
            i += 1
            while i < len(lines) and depth:
                block.append(lines[i])
                stripped = lines[i].strip()
                if "struct.begin" in stripped:
                    depth += 1
                if stripped == "struct.end":
                    depth -= 1
                i += 1
            block, placement = patch_block(block, hint, configs)
            out.extend(block)
            if placement and placement not in placements:
                placements.append(placement)
            continue
        out.append(line)
        i += 1
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return placements


def main() -> None:
    configs = load_configs()
    print("Applying BPRUE module layout from per-family vanilla modification columns")
    for weapon_class in GROUP_ORDER:
        setups = [setup for _, setup in family_records(configs, weapon_class)]
        maxima = modification_max_columns_for_general_setups(setups)
        print(
            f"  {weapon_class} vanilla family maxima: "
            + (", ".join(f"{k}={v}" for k, v in sorted(maxima.items())) or "none")
        )

    for path in FILES:
        placements = process(path, configs)
        if placements:
            formatted = ", ".join(
                f"{target}/{group}={column} [{','.join(setups)}]"
                for target, group, column, setups in placements
            )
            print(f"Applied module columns to {path.name}: {formatted}")


if __name__ == "__main__":
    main()
