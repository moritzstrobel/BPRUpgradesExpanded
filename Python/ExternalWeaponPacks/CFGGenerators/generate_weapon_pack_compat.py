from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = ROOT / "Python"
COMMON = PYTHON_ROOT / "CFGGenerators/Common"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))

from CFGGenerators.AssaultRifles import generate_assault_rifle_upgrades as ar  # noqa: E402
from ExternalWeaponPacks.Analysis.analyze_weapon_packs import DEFAULT_VANILLA_ROOT, collect_family, collect_upgrade_definitions, effective_entry, game_data_roots, load_registry, technician_owners  # noqa: E402
from upgrade_build_model import UpgradeBuildModel  # noqa: E402
from upgrade_renderers import render_consolidated_upgrade_prototypes, render_general_setup_patch  # noqa: E402

DEFAULT_OUTPUT = ROOT / "Compat/WeaponPacks/GameLite"
GENERIC_IMAGE_BY_CALIBER = {
    "A545": "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/AK74/Barrel/Upgrade/T_AK47_Upg_a_1.T_AK47_Upg_a_1'",
    "A556": "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/G37/Barrel/Upgrade/T_GP_upgr_3.T_GP_upgr_3'",
    "A762": "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/AK74/Barrel/Upgrade/T_AK47_Upg_a_1.T_AK47_Upg_a_1'",
    "A762NATO": "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/G37/Barrel/Upgrade/T_GP_upgr_3.T_GP_upgr_3'",
}
NO_POWER_CONVERSION = {"A762", "A762NATO"}


def build_pack_model(pack_name: str, spec: dict) -> UpgradeBuildModel:
    if spec["category"] != "AssaultRifle":
        raise ValueError(f"{pack_name}: unsupported category {spec['category']}")
    base_config = ar.load_config()
    config = {"families": {}, "module_groups": base_config["module_groups"]}
    for weapon in spec["weapons"]:
        family = {
            "weapon_sid": weapon["weapon_sid"],
            "general_setup_sid": weapon["general_setup_sid"],
            "prototype_prefix": weapon["prototype_prefix"],
            "base_caliber": weapon["base_caliber"],
            "image": GENERIC_IMAGE_BY_CALIBER[weapon["base_caliber"]],
        }
        if weapon["base_caliber"] in NO_POWER_CONVERSION:
            family["bprue_caliber_conversion"] = False
        config["families"][weapon["weapon_sid"]] = family

    model = UpgradeBuildModel()
    model.extend(ar.build_upgrades(config))
    burst_count = model.configure_general_setups_for_effect("BPRUE_AddBurstFireModeEffect", FireQueueCount=3)
    model.validate()
    print(f"{pack_name}: {model.summary()}, burst setups={burst_count}")
    return model


def pack_sources(spec: dict, vanilla_root: Path):
    root = vanilla_root / spec["reference_root"]
    roots = game_data_roots(root)
    if not roots:
        raise FileNotFoundError(f"No GameData root found below {root}")
    setups, upgrade_defs = {}, set()
    for game_data in roots:
        setups.update(collect_family(game_data, "WeaponGeneralSetupPrototypes"))
        upgrade_defs.update(collect_upgrade_definitions(game_data))
    return roots, setups, upgrade_defs


def validate_pack(pack_name: str, spec: dict, vanilla_root: Path) -> dict[str, list[str]]:
    roots, setups, upgrade_defs = pack_sources(spec, vanilla_root)
    errors, all_roots = [], set()
    for weapon in spec["weapons"]:
        setup_sid = weapon["general_setup_sid"]
        setup = setups.get(setup_sid)
        if setup is None:
            errors.append(f"{weapon['weapon_sid']}: missing GeneralSetup {setup_sid}")
            continue
        effective_fields, inheritance_chain = effective_entry(setups, setup_sid)
        detected = effective_fields.get("AmmoCaliber")
        if detected and detected != weapon["base_caliber"]:
            errors.append(f"{weapon['weapon_sid']}: registry caliber {weapon['base_caliber']} != effective CFG {detected}")
        pack_roots = effective_fields.get("UpgradePrototypeSIDs", [])
        if not pack_roots:
            print(f"{pack_name}: {weapon['weapon_sid']} has no native upgrade roots; BPRUE modules will initialize the upgrade list")
        if len(inheritance_chain) > 1:
            print(f"{pack_name}: {weapon['weapon_sid']} setup inheritance: {' -> '.join(inheritance_chain)}")
        all_roots.update(pack_roots)

    print(f"{pack_name}: source upgrade roots={len(all_roots)}, locally defined={len(all_roots & upgrade_defs)}, external/Vanilla={len(all_roots - upgrade_defs)}")
    technicians: dict[str, list[str]] = defaultdict(list)
    for game_data in roots:
        for technician_sid, owned in technician_owners(game_data, all_roots).items():
            technicians[technician_sid].extend(owned)
    if errors:
        raise ValueError(f"{pack_name} validation failed:\n  - " + "\n  - ".join(errors))
    return {sid: sorted(set(values)) for sid, values in technicians.items()}


def render_technicians(pack_name: str, model: UpgradeBuildModel, technicians: dict[str, list[str]]) -> str:
    upgrades = model.technician_upgrades()
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        f"// BPRUE technician additions for external weapon pack: {pack_name}",
        "// A technician receives BPRUE modules only when the source pack already",
        "// grants that technician at least one upgrade used by this weapon pack.",
        "// -----------------------------------------------------------------------------", "",
    ]
    for technician_sid in sorted(technicians):
        list_sid = f"BPRUE_{pack_name}_{technician_sid}_UpgradeList"
        lines.append(f"{list_sid} : struct.begin")
        for upgrade in upgrades:
            lines += [f"   {upgrade.sid} : struct.begin", f"      UpgradePrototypeSID = {upgrade.sid}", "      Enabled = true", "   struct.end"]
        lines += ["struct.end", "", f"{technician_sid} : struct.begin {{bpatch}}", f"   Upgrades : struct.begin {{bpatch;refkey={list_sid}}}", "   struct.end", "struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path.relative_to(ROOT).as_posix()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate BPRUE Assault Rifle support for registered external weapon packs.")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    registry = load_registry()
    for pack_name, spec in registry["packs"].items():
        model = build_pack_model(pack_name, spec)
        technicians = validate_pack(pack_name, spec, args.vanilla_root)
        pack_root = args.output_root / pack_name / "GameData"
        write(pack_root / "UpgradePrototypes/UpgradePrototypes_patch_BPRUE_WeaponPack.cfg", render_consolidated_upgrade_prototypes(model))
        write(pack_root / "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_WeaponPack.cfg", render_general_setup_patch(model, header_comments=(f"External pack: {pack_name}", "Appends BPRUE Assault Rifle modules without replacing the pack's own upgrade roots.")))
        write(pack_root / "NPCPrototypes/NPCPrototypes_patch_BPRUE_WeaponPack.cfg", render_technicians(pack_name, model, technicians))
        print(f"{pack_name}: technicians={len(technicians)}")
    print("\nBPRUE x external weapon packs generated. OXA interaction is intentionally not handled here.")


if __name__ == "__main__":
    main()
