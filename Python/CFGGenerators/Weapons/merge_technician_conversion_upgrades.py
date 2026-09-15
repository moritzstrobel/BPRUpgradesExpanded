from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
AR_CONFIG_PATH = SCRIPT_DIR / "assault_rifles_upgrades.json"
SHOTGUN_CONFIG_PATH = SCRIPT_DIR / "shotgun_upgrades.json"
PISTOL_CONFIG_PATH = SCRIPT_DIR / "pistol_upgrades.json"
NPC_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "NPCPrototypes" / "NPCPrototypes_patch_BPRUE.cfg"

CONVERSION_UPGRADE_SIDS = [
    "GunViper_Upgrade_BPRUE_PistolConversion", "GunAKU_Upgrade_BPRUE_PistolConversion",
    "GunBucket_Upgrade_BPRUE_PistolConversion", "GunIntegral_Upgrade_BPRUE_PistolConversion",
    "GunZubr_Upgrade_BPRUE_PistolConversion", "GunFora230_Upgrade_BPRUE_PistolConversion",
]
SMG_MODULE_SIDS = [
    "BPRUE_SMG_Upgrade_Readiness_QuickDraw", "BPRUE_SMG_Upgrade_Readiness_Stabilized",
    "BPRUE_SMG_Upgrade_Reload_Competition", "BPRUE_SMG_Upgrade_Reload_Tactical",
    "BPRUE_SMG_Upgrade_Action_HighSpeed", "BPRUE_SMG_Upgrade_Action_Controlled",
]
SMG_CALIBER_SIDS = [
    "GunViper_Upgrade_BPRUE_Caliber_A918", "GunViper_Upgrade_BPRUE_Caliber_A045",
    "GunBucket_Upgrade_BPRUE_Caliber_A919", "GunBucket_Upgrade_BPRUE_Caliber_A045",
    "GunIntegral_Upgrade_BPRUE_Caliber_A918", "GunIntegral_Upgrade_BPRUE_Caliber_A045",
    "GunZubr_Upgrade_BPRUE_Caliber_A918", "GunZubr_Upgrade_BPRUE_Caliber_A045",
    "GunFora230_Upgrade_BPRUE_Caliber_A918", "GunFora230_Upgrade_BPRUE_Caliber_A045",
    "GunM10_Upgrade_BPRUE_Caliber_A919", "GunM10_Upgrade_BPRUE_Caliber_A918",
]


def load_technician_sids() -> list[str]:
    config = json.loads(AR_CONFIG_PATH.read_text(encoding="utf-8"))
    technician = config["technician"]
    return list(dict.fromkeys([technician["prototype_sid"], technician["all_prototype_sid"], *technician.get("concrete_prototype_sids", [])]))


def shotgun_module_sids() -> list[str]:
    config = json.loads(SHOTGUN_CONFIG_PATH.read_text(encoding="utf-8"))
    result: list[str] = []
    for family in config["families"].values():
        prefix = family["prototype_prefix"]
        for group, choices in config["module_groups"].items():
            group_name = group.title()
            for choice in choices:
                result.append(f"{prefix}_Upgrade_BPRUE_SG_{group_name}_{choice.title().replace('_', '')}")
    return result


def pistol_module_sids() -> list[str]:
    config = json.loads(PISTOL_CONFIG_PATH.read_text(encoding="utf-8"))
    result: list[str] = []
    for family in config["families"].values():
        prefix = family["prototype_prefix"]
        for group, choices in config["module_groups"].items():
            group_name = group.title()
            for choice in choices:
                result.append(f"{prefix}_Upgrade_BPRUE_Pistol_{group_name}_{choice.title().replace('_', '')}")
        signature = family["signature"].title().replace("_", "")
        result.append(f"{prefix}_Upgrade_BPRUE_Pistol_Signature_{signature}")
    return result


def merge_into_technician_block(content: str, technician_sid: str, upgrade_sids: list[str]) -> str:
    block_start = f"{technician_sid} : struct.begin {{bpatch}}\n"
    start = content.find(block_start)
    if start < 0:
        raise ValueError(f"Technician block not found: {technician_sid}")
    next_block = content.find("\nstruct.end\n", start)
    if next_block < 0:
        raise ValueError(f"Technician block is not closed: {technician_sid}")
    block = content[start:next_block + len("\nstruct.end\n")]
    missing = [sid for sid in upgrade_sids if sid not in block]
    if not missing:
        return content
    marker = "   Upgrades : struct.begin {bpatch}\n"
    marker_pos = block.find(marker)
    if marker_pos < 0:
        raise ValueError(f"Upgrades block not found: {technician_sid}")
    insert_pos = start + marker_pos + len(marker)
    entries: list[str] = []
    for sid in missing:
        entries += ["      [*] : struct.begin", f"         UpgradePrototypeSID = {sid}", "         Enabled = true", "      struct.end"]
    return content[:insert_pos] + "\n".join(entries) + "\n" + content[insert_pos:]


def main() -> None:
    content = NPC_OUTPUT_PATH.read_text(encoding="utf-8")
    upgrade_sids = CONVERSION_UPGRADE_SIDS + SMG_MODULE_SIDS + SMG_CALIBER_SIDS + shotgun_module_sids() + pistol_module_sids()
    for technician_sid in load_technician_sids():
        content = merge_into_technician_block(content, technician_sid, upgrade_sids)
    for old_comment in (
        "// Draft setup: all BPRUE assault-rifle modules are available at all technicians.",
        "// All BPRUE assault-rifle modules, SMG specialization/caliber modules and pistol-conversion upgrades are available at all technicians.",
        "// All BPRUE assault-rifle, SMG and shotgun specialization modules are available at all technicians.",
        "// All BPRUE assault-rifle, SMG, shotgun and pistol signature modules are available at all technicians.",
    ):
        content = content.replace(old_comment, "// All BPRUE assault-rifle, SMG, shotgun and pistol specialization modules are available at all technicians.")
    NPC_OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Merged SMG, shotgun and pistol specialization upgrades into {NPC_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
