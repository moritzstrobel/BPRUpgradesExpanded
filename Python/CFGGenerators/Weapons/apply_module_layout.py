from __future__ import annotations

import re
from pathlib import Path

from vanilla_upgrade_layout import group_columns, vanilla_modification_max_columns

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

# Each logical module group gets one column. Columns are allocated independently
# per target part, immediately to the right of the highest vanilla modification
# column found in Python/VanillaReference/UpgradePrototypes.cfg.
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
        # SMG caliber upgrades live in the SMG split file; AR caliber upgrades
        # live in the AR base file. The caller supplies the file class hint.
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


def patch_block(block: list[str], hint: str) -> tuple[list[str], tuple[str, str, int] | None]:
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
    column = group_columns(target, groups)[group]

    new_line = f"   HorizontalPosition = {column}"
    if horizontal_index is not None:
        block[horizontal_index] = new_line
    else:
        insert_at = next(
            (i for i, line in enumerate(block) if line.strip().startswith("VerticalPosition =")),
            len(block) - 1,
        )
        block.insert(insert_at, new_line)
    return block, (target, group, column)


def process(path: Path) -> list[tuple[str, str, int]]:
    if not path.exists():
        raise FileNotFoundError(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    placements: list[tuple[str, str, int]] = []
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
            block, placement = patch_block(block, hint)
            out.extend(block)
            if placement and placement not in placements:
                placements.append(placement)
            continue
        out.append(line)
        i += 1
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return placements


def main() -> None:
    maxima = vanilla_modification_max_columns()
    print("Vanilla modification max columns: " + ", ".join(f"{k}={v}" for k, v in sorted(maxima.items())))
    for path in FILES:
        placements = process(path)
        if placements:
            formatted = ", ".join(f"{target}/{group}={column}" for target, group, column in placements)
            print(f"Applied module columns to {path.name}: {formatted}")


if __name__ == "__main__":
    main()
