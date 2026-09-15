from __future__ import annotations

from pathlib import Path

import generate_assault_rifle_upgrades as ar
import generate_pistol_upgrades as pistol
import generate_shotgun_upgrades as shotgun
import generate_smg_upgrades as smg
import generate_sniper_upgrades as sniper
from upgrade_build_model import UpgradeBuildModel

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
NPC_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "NPCPrototypes" / "NPCPrototypes_patch_BPRUE.cfg"


def load_technician_sids() -> list[str]:
    config = ar.load_config()
    technician = config["technician"]
    return list(dict.fromkeys([
        technician["prototype_sid"],
        technician["all_prototype_sid"],
        *technician.get("concrete_prototype_sids", []),
    ]))


def collect_upgrade_sids() -> list[str]:
    """Use the same class builders as the CFG generators; never reconstruct SIDs here."""
    model = UpgradeBuildModel()
    model.extend(ar.build_upgrades(ar.load_config()))
    model.extend(smg.build_upgrades(smg.load_config()))
    model.extend(shotgun.build_upgrades(shotgun.cfg()))
    model.extend(pistol.build_upgrades(pistol.load_config()))
    model.extend(sniper.build_upgrades(sniper.load_config()))
    model.validate()
    return list(dict.fromkeys(upgrade.sid for upgrade in model.technician_upgrades()))


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
        entries += [
            "      [*] : struct.begin",
            f"         UpgradePrototypeSID = {sid}",
            "         Enabled = true",
            "      struct.end",
        ]
    return content[:insert_pos] + "\n".join(entries) + "\n" + content[insert_pos:]


def main() -> None:
    content = NPC_OUTPUT_PATH.read_text(encoding="utf-8")
    upgrade_sids = collect_upgrade_sids()
    for technician_sid in load_technician_sids():
        content = merge_into_technician_block(content, technician_sid, upgrade_sids)

    for old_comment in (
        "// Draft setup: all BPRUE assault-rifle modules are available at all technicians.",
        "// All BPRUE assault-rifle modules, SMG specialization/caliber modules and pistol-conversion upgrades are available at all technicians.",
        "// All BPRUE assault-rifle, SMG and shotgun specialization modules are available at all technicians.",
        "// All BPRUE assault-rifle, SMG, shotgun and pistol signature modules are available at all technicians.",
        "// All BPRUE assault-rifle, SMG, shotgun and pistol specialization modules are available at all technicians.",
    ):
        content = content.replace(
            old_comment,
            "// All BPRUE weapon specialization modules are available at all technicians.",
        )

    NPC_OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Merged {len(upgrade_sids)} model-backed specialization upgrades into {NPC_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
