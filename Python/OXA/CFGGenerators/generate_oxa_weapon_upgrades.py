from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = ROOT / "Python"
COMMON = PYTHON_ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))

from generate_all_cfg import build_model  # noqa: E402
from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition  # noqa: E402
from upgrade_renderers import render_consolidated_upgrade_prototypes  # noqa: E402
from technician_support import vanilla_technician_general_setups  # noqa: E402

OUTPUT_ROOT = ROOT / "Compat/OXA/GameLite"

# OXA-only weapon support deliberately lives in the compat package. The normal
# BPRUE build must never reference these SIDs.
FAMILIES = {
    "GunAKS74N_G2_ST": {
        "source_setup": "GunAK74_ST",
        "target_prefix": "GunAKS74N_G2",
    },
    "GunGlock17_HG": {
        "source_setup": "GunUDP_HG",
        "target_prefix": "GunGlock17",
    },
    "GunP30L_HG": {
        "source_setup": "GunUDP_HG",
        "target_prefix": "GunP30L",
    },
}


def _clone_sid(source_sid: str, source_prefix: str, target_prefix: str) -> str:
    prefix = f"{source_prefix}_Upgrade_BPRUE_"
    if not source_sid.startswith(prefix):
        raise ValueError(f"{source_sid}: expected BPRUE family prefix {prefix}")
    return f"{target_prefix}_Upgrade_BPRUE_{source_sid[len(prefix):]}"


def _source_prefix(upgrades: list[UpgradeDefinition]) -> str:
    prefixes = {
        upgrade.sid.split("_Upgrade_BPRUE_", 1)[0]
        for upgrade in upgrades
        if "_Upgrade_BPRUE_" in upgrade.sid
    }
    if len(prefixes) != 1:
        raise ValueError(f"Expected one source prefix, got {sorted(prefixes)}")
    return next(iter(prefixes))


def build_oxa_model() -> tuple[UpgradeBuildModel, dict[str, str]]:
    source_model, _ = build_model()
    target = UpgradeBuildModel()
    source_setup_by_target: dict[str, str] = {}

    for target_setup, spec in FAMILIES.items():
        source_setup = spec["source_setup"]
        source_upgrades = [
            upgrade
            for upgrade in source_model.upgrades
            if source_setup in upgrade.general_setup_sids
        ]
        if not source_upgrades:
            raise ValueError(f"No BPRUE upgrades found for source family {source_setup}")

        source_prefix = _source_prefix(source_upgrades)
        sid_map = {
            upgrade.sid: _clone_sid(upgrade.sid, source_prefix, spec["target_prefix"])
            for upgrade in source_upgrades
        }

        for upgrade in source_upgrades:
            target.add(replace(
                upgrade,
                sid=sid_map[upgrade.sid],
                general_setup_sid=target_setup,
                additional_general_setup_sids=(),
                blocking_sids=tuple(sid_map.get(sid, sid) for sid in upgrade.blocking_sids),
                required_upgrade_sids=tuple(sid_map.get(sid, sid) for sid in upgrade.required_upgrade_sids),
            ))
        source_setup_by_target[target_setup] = source_setup

    target.validate()
    return target, source_setup_by_target


def render_general_setup(model: UpgradeBuildModel) -> str:
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// OXA-only weapons receive cloned BPRUE family upgrades.",
        "// This file belongs exclusively to the OXA compatibility package.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for setup_sid, upgrades in model.by_general_setup().items():
        # OXA owns the baseline array for these weapons. Emit one complete,
        # deterministic indexed array: existing OXA entries first, then BPRUE.
        # GunAKS74N_G2_ST currently reuses the eight Vanilla AK74 roots; the
        # two OXA pistols intentionally start with no upgrade roots.
        baseline = {
            "GunAKS74N_G2_ST": [
                "GunAK74_Upgrade_Barrel_1",
                "GunAK74_Upgrade_Barrel_2_1",
                "GunAK74_Upgrade_Barrel_2_2",
                "GunAK74_Upgrade_Body_1",
                "GunAK74_Upgrade_Body_2",
                "GunAK74_Upgrade_Stock_1",
                "GunAK74_Upgrade_Stock_2",
                "GunAK74_Upgrade_Stock_3",
            ],
            "GunGlock17_HG": [],
            "GunP30L_HG": [],
        }[setup_sid]
        combined = list(dict.fromkeys([*baseline, *(upgrade.sid for upgrade in upgrades)]))
        lines += [
            f"{setup_sid} : struct.begin {{bpatch}}",
            "   UpgradePrototypeSIDs : struct.begin",
            *(f"      [{index}] = {sid}" for index, sid in enumerate(combined)),
            "   struct.end",
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def render_npc_patch(model: UpgradeBuildModel, source_setup_by_target: dict[str, str]) -> str:
    support = vanilla_technician_general_setups()
    assignments: dict[str, list[UpgradeDefinition]] = defaultdict(list)

    for target_setup, upgrades in model.by_general_setup().items():
        source_setup = source_setup_by_target[target_setup]
        for technician_sid, supported_setups in support.items():
            if source_setup in supported_setups:
                assignments[technician_sid].extend(upgrades)

    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// OXA-only BPRUE upgrades follow the technician availability of their source family.",
        "// Append to BPRUE's already materialized technician Upgrades nodes.",
        "// This preserves Base/DLC/Edition registrations from earlier packages.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for technician_sid, upgrades in sorted(assignments.items()):
        unique = list({upgrade.sid: upgrade for upgrade in upgrades}.values())
        if not unique:
            continue
        lines += [
            f"{technician_sid} : struct.begin {{bpatch}}",
            "   Upgrades : struct.begin {bpatch}",
        ]
        for upgrade in unique:
            lines += [
                "      [*] : struct.begin",
                f"         UpgradePrototypeSID = {upgrade.sid}",
                "         Enabled = true",
                "      struct.end",
            ]
        lines += ["   struct.end", "struct.end", ""]

    return "\n".join(lines).rstrip() + "\n"

def write(relative: str, content: str) -> Path:
    path = OUTPUT_ROOT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def main() -> None:
    model, source_setup_by_target = build_oxa_model()
    outputs = [
        write(
            "GameData/UpgradePrototypes/UpgradePrototypes_patch_BPRUE_OXA_Weapons.cfg",
            render_consolidated_upgrade_prototypes(model),
        ),
        write(
            "GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_OXA_Weapons.cfg",
            render_general_setup(model),
        ),
        write(
            "GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE_OXA_Weapons.cfg",
            render_npc_patch(model, source_setup_by_target),
        ),
    ]
    print("BPRUE OXA weapon-family integration")
    print("===================================")
    for target_setup, source_setup in source_setup_by_target.items():
        count = len(model.by_general_setup()[target_setup])
        print(f"{target_setup}: {source_setup} family -> {count} cloned upgrades")
    for path in outputs:
        print(f"Wrote {path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
