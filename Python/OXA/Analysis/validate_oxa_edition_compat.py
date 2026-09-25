from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
ROOT = PYTHON_ROOT.parent
COMMON = PYTHON_ROOT / "CFGGenerators" / "Common"
OXA_CFG = PYTHON_ROOT / "OXA" / "CFGGenerators"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))
sys.path.insert(0, str(OXA_CFG))

from generate_all_cfg import build_edition_outputs, build_model
from edition_weapon_modules import load_edition_config
from dlc_weapon_modules import CLASS_CONFIG_KEYS
from generate_oxa_edition_compat import BASE_COMPAT, OXA_COMPAT_ROOT, _setup_arrays

def main() -> None:
    if not BASE_COMPAT.exists():
        raise FileNotFoundError(BASE_COMPAT)

    base_arrays = _setup_arrays(BASE_COMPAT.read_text(encoding="utf-8"))
    source_model, configs = build_model(apply_layout=False)
    edition_models = build_edition_outputs(source_model, configs)
    weapons = load_edition_config().get("weapons", {})

    errors: list[str] = []
    checked = 0
    skipped = 0

    for name, weapon in weapons.items():
        pack = weapon["content_pack"]
        target_setup = weapon["general_setup_sid"]
        config_key = CLASS_CONFIG_KEYS[weapon["class"]]
        base_setup = configs[config_key]["families"][weapon["base_family"]]["general_setup_sid"]
        base_compat = base_arrays.get(base_setup)

        target_path = (
            OXA_COMPAT_ROOT
            / "DLCGameData"
            / pack
            / "WeaponData"
            / "WeaponGeneralSetupPrototypes"
            / "WeaponGeneralSetupPrototypes_patch_BPRUE_OXA_Editions.cfg"
        )
        target_arrays = _setup_arrays(target_path.read_text(encoding="utf-8")) if target_path.exists() else {}

        if base_compat is None:
            skipped += 1
            if target_setup in target_arrays:
                errors.append(f"{pack}/{name}: unexpected OXA Edition projection for unchanged base {base_setup}")
            continue

        checked += 1
        actual = target_arrays.get(target_setup)
        if actual is None:
            errors.append(f"{pack}/{name}: missing projected array for {target_setup}")
            continue

        expected_core = [sid for sid in base_compat if not sid.startswith("BPRUE")]
        expected_bprue = [
            upgrade.sid
            for upgrade in edition_models[pack].by_general_setup().get(target_setup, [])
        ]
        expected = expected_core + expected_bprue

        if actual != expected:
            errors.append(
                f"{pack}/{name}: projected array differs from expected OXA core + Edition BPRUE "
                f"(expected {len(expected)}, got {len(actual)})"
            )
        leaked_base_bprue = [
            sid for sid in actual
            if sid.startswith("BPRUE") and sid not in set(expected_bprue)
        ]
        if leaked_base_bprue:
            errors.append(
                f"{pack}/{name}: base/non-Edition BPRUE SIDs leaked into projection: "
                + ", ".join(leaked_base_bprue)
            )
        if actual[:len(expected_core)] != expected_core:
            errors.append(f"{pack}/{name}: OXA core order/content was not preserved")
        if actual[len(expected_core):] != expected_bprue:
            errors.append(f"{pack}/{name}: Edition BPRUE suffix order/content was not preserved")

    print("BPRUE Editions <-> OXA compatibility validation")
    print("================================================")
    print(f"Edition weapons: {len(weapons)}")
    print(f"Projected:       {checked}")
    print(f"Unchanged:       {skipped}")
    print(f"Errors:          {len(errors)}")
    if errors:
        print("\nErrors:")
        for error in errors:
            print(f"  - {error}")
        raise ValueError("Edition/OXA compatibility validation failed.")
    print("\nVALID")


if __name__ == "__main__":
    main()
