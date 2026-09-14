from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent

CONFIG_PATH = SCRIPT_DIR / "assault_rifles_upgrades.json"
NPC_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "NPCPrototypes" / "NPCPrototypes_patch_BPRUE.cfg"

CONVERSION_UPGRADE_SIDS = [
    "GunViper_Upgrade_BPRUE_PistolConversion",
    "GunAKU_Upgrade_BPRUE_PistolConversion",
    "GunBucket_Upgrade_BPRUE_PistolConversion",
    "GunIntegral_Upgrade_BPRUE_PistolConversion",
    "GunZubr_Upgrade_BPRUE_PistolConversion",
    "GunFora230_Upgrade_BPRUE_PistolConversion",
]


def load_technician_sids() -> list[str]:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    technician = config["technician"]
    result = [
        technician["prototype_sid"],
        technician["all_prototype_sid"],
        *technician.get("concrete_prototype_sids", []),
    ]
    return list(dict.fromkeys(result))


def render_entries(indent: str = "      ") -> str:
    lines: list[str] = []
    for sid in CONVERSION_UPGRADE_SIDS:
        lines.extend(
            [
                f"{indent}[*] : struct.begin",
                f"{indent}   UpgradePrototypeSID = {sid}",
                f"{indent}   Enabled = true",
                f"{indent}struct.end",
            ]
        )
    return "\n".join(lines) + "\n"


def merge_into_technician_block(content: str, technician_sid: str) -> str:
    block_start = f"{technician_sid} : struct.begin {{bpatch}}\n"
    start = content.find(block_start)
    if start < 0:
        raise ValueError(f"Technician block not found: {technician_sid}")

    next_block = content.find("\nstruct.end\n", start)
    if next_block < 0:
        raise ValueError(f"Technician block is not closed: {technician_sid}")

    block_end = next_block + len("\nstruct.end\n")
    block = content[start:block_end]

    missing = [sid for sid in CONVERSION_UPGRADE_SIDS if sid not in block]
    if not missing:
        return content

    marker = "   Upgrades : struct.begin {bpatch}\n"
    marker_pos = block.find(marker)
    if marker_pos < 0:
        raise ValueError(f"Upgrades block not found: {technician_sid}")

    insert_pos = start + marker_pos + len(marker)
    entries: list[str] = []
    for sid in missing:
        entries.extend(
            [
                "      [*] : struct.begin",
                f"         UpgradePrototypeSID = {sid}",
                "         Enabled = true",
                "      struct.end",
            ]
        )

    return content[:insert_pos] + "\n".join(entries) + "\n" + content[insert_pos:]


def main() -> None:
    content = NPC_OUTPUT_PATH.read_text(encoding="utf-8")

    for technician_sid in load_technician_sids():
        content = merge_into_technician_block(content, technician_sid)

    content = content.replace(
        "// Draft setup: all BPRUE assault-rifle modules are available at all technicians.",
        "// All BPRUE assault-rifle modules and pistol-conversion upgrades are available at all technicians.",
    )

    NPC_OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Merged pistol-conversion upgrades into {NPC_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
