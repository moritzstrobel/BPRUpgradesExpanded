from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
ROOT = PYTHON_ROOT.parent
COMMON = PYTHON_ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))

from generate_all_cfg import build_edition_outputs, build_model
from edition_weapon_modules import load_edition_config
from dlc_weapon_modules import CLASS_CONFIG_KEYS
from vanilla_upgrade_layout import dlc_general_setup_upgrades, vanilla_general_setup_upgrades

OXA_COMPAT_ROOT = ROOT / "Compat" / "OXA" / "GameLite"
BASE_COMPAT = (
    OXA_COMPAT_ROOT
    / "GameData"
    / "WeaponData"
    / "WeaponGeneralSetupPrototypes"
    / "WeaponGeneralSetupPrototypes_patch_BPRUE_OXA.cfg"
)

SETUP_BLOCK_RE = re.compile(
    r"(?ms)^([A-Za-z0-9_]+)\s*:\s*struct\.begin\s*\{bpatch\}\s*\n"
    r"(.*?)(?=^[A-Za-z0-9_]+\s*:\s*struct\.begin\s*\{bpatch\}|\Z)"
)
UPGRADE_ARRAY_RE = re.compile(
    r"(?ms)^\s*UpgradePrototypeSIDs\s*:\s*struct\.begin\s*\n"
    r"(.*?)^\s*struct\.end"
)
ARRAY_VALUE_RE = re.compile(r"^\s*\[\d+\]\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)


def _setup_arrays(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for sid, body in SETUP_BLOCK_RE.findall(text):
        match = UPGRADE_ARRAY_RE.search(body)
        if match:
            result[sid] = ARRAY_VALUE_RE.findall(match.group(1))
    return result


def _render_setup(setup_sid: str, values: list[str], *, base_setup: str, pack: str) -> str:
    lines = [
        f"// {pack}: projected from OXA-compatible base setup {base_setup}",
        f"{setup_sid} : struct.begin {{bpatch}}",
        "   UpgradePrototypeSIDs : struct.begin",
    ]
    lines.extend(f"      [{index}] = {sid}" for index, sid in enumerate(values))
    lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def generate() -> tuple[list[Path], list[dict]]:
    if not BASE_COMPAT.exists():
        raise FileNotFoundError(
            f"{BASE_COMPAT} does not exist. Generate the normal OXA compatibility patch first."
        )

    base_compat_arrays = _setup_arrays(BASE_COMPAT.read_text(encoding="utf-8"))
    base_vanilla_arrays = vanilla_general_setup_upgrades()

    source_model, configs = build_model(apply_layout=False)
    edition_models = build_edition_outputs(source_model, configs)
    edition_config = load_edition_config().get("weapons", {})

    by_pack: dict[str, list[dict]] = defaultdict(list)
    skipped: list[dict] = []

    for name, weapon in edition_config.items():
        pack = weapon["content_pack"]
        class_name = weapon["class"]
        config_key = CLASS_CONFIG_KEYS[class_name]
        family = configs[config_key]["families"][weapon["base_family"]]
        base_setup = family["general_setup_sid"]
        target_setup = weapon["general_setup_sid"]

        base_compat = base_compat_arrays.get(base_setup)
        if base_compat is None:
            skipped.append({
                "weapon": name,
                "pack": pack,
                "target_setup": target_setup,
                "base_setup": base_setup,
                "reason": "base setup has no generated OXA/BPRUE UpgradePrototypeSIDs compatibility array",
            })
            continue

        base_vanilla = base_vanilla_arrays.get(base_setup, [])
        edition_vanilla = dlc_general_setup_upgrades(pack).get(target_setup, [])
        if not base_vanilla:
            raise ValueError(f"{name}: no Vanilla UpgradePrototypeSIDs found for base setup {base_setup}")
        if edition_vanilla != base_vanilla:
            raise ValueError(
                f"{name}: Edition Vanilla array differs from base family {base_setup}; "
                "automatic OXA projection would be unsafe"
            )

        # The normal OXA compat array is already the validated effective
        # OXA + (BPRUE - Vanilla) state for the base family.  Remove BPRUE's
        # base-family clones and replace them with this Edition weapon's clones.
        oxa_core = [sid for sid in base_compat if not sid.startswith("BPRUE")]
        edition_upgrades = [
            upgrade.sid
            for upgrade in edition_models[pack].by_general_setup().get(target_setup, [])
        ]
        if not edition_upgrades:
            raise ValueError(f"{name}: no generated Edition BPRUE upgrades for {target_setup}")

        final = oxa_core + edition_upgrades
        duplicates = sorted({sid for sid in final if final.count(sid) > 1})
        if duplicates:
            raise ValueError(f"{name}: duplicate projected upgrade SIDs: {', '.join(duplicates)}")

        by_pack[pack].append({
            "weapon": name,
            "target_setup": target_setup,
            "base_setup": base_setup,
            "base_vanilla": base_vanilla,
            "oxa_core": oxa_core,
            "edition_upgrades": edition_upgrades,
            "final": final,
        })

    written: list[Path] = []
    for pack, entries in sorted(by_pack.items()):
        target = (
            OXA_COMPAT_ROOT
            / "DLCGameData"
            / pack
            / "WeaponData"
            / "WeaponGeneralSetupPrototypes"
            / "WeaponGeneralSetupPrototypes_patch_BPRUE_OXA_Editions.cfg"
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "// -----------------------------------------------------------------------------",
            "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
            "// BPRUE Editions <-> OXA compatibility projection",
            "// Effective state: OXA base-family state + Edition-specific BPRUE clones",
            "// Generated only for Edition weapons whose base family requires OXA compat.",
            "// -----------------------------------------------------------------------------",
            "",
        ]
        for entry in sorted(entries, key=lambda value: value["target_setup"]):
            lines.append(_render_setup(
                entry["target_setup"],
                entry["final"],
                base_setup=entry["base_setup"],
                pack=pack,
            ))
        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        written.append(target)

    return written, skipped


def main() -> None:
    written, skipped = generate()
    print("BPRUE Editions <-> OXA compatibility projection")
    print("================================================")
    for path in written:
        print(f"Wrote {path.relative_to(ROOT).as_posix()}")
    if skipped:
        print("\nEdition weapons requiring no UpgradePrototypeSIDs projection:")
        for item in skipped:
            print(
                f"  {item['pack']}/{item['weapon']}: {item['base_setup']} -> "
                f"{item['target_setup']} ({item['reason']})"
            )
    print(f"\nGenerated files: {len(written)}")
    print(f"Unchanged Edition weapons: {len(skipped)}")


if __name__ == "__main__":
    main()
