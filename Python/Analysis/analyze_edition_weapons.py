from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
CFG_ROOT = PYTHON_ROOT / "CFGGenerators"
COMMON = CFG_ROOT / "Common"
VANILLA_ROOT = PYTHON_ROOT / "VanillaReference"
DLC_ROOT = VANILLA_ROOT / "DLCGameData"
REPORT_PATH = SCRIPT_DIR / "Reports" / "edition_weapon_analysis.json"
EDITION_PACKS = ("Deluxe", "PreOrder", "Ultimate")

sys.path.insert(0, str(SCRIPT_DIR))
from analyze_weapon_coverage import (  # noqa: E402
    CONFIGS,
    base_weapon_index,
    configured_weapons,
    direct_array_values,
    direct_scalar,
    inheritance_chain,
    refkey,
    refurl,
    resolve_dlc_item_base,
    resolve_setup_base,
    top_level_blocks,
)

VANILLA_WEAPONS = VANILLA_ROOT / "WeaponPrototypes.cfg"
VANILLA_SETUPS = VANILLA_ROOT / "WeaponGeneralSetupPrototypes.cfg"


def _combined_chain(sid: str, local: dict[str, list[str]], vanilla: dict[str, list[str]]) -> list[str]:
    return inheritance_chain(sid, {**vanilla, **local})


def _family_setup(configured: dict[str, dict], weapon_class: str, family: str) -> str | None:
    for entry in configured.values():
        if entry.get("class") == weapon_class and entry.get("family") == family:
            return entry.get("general_setup_sid")
    return None


def _linked_weapons(setup_sid: str, local_items: dict[str, list[str]], vanilla_items: dict[str, list[str]]) -> list[dict]:
    combined = {**vanilla_items, **local_items}
    rows = []
    for weapon_sid, block in sorted(local_items.items()):
        if direct_scalar(block, "GeneralWeaponSetup") != setup_sid:
            continue
        rows.append({
            "weapon_sid": weapon_sid,
            "direct_refkey": refkey(block),
            "direct_refurl": refurl(block),
            "inheritance_chain": _combined_chain(weapon_sid, local_items, vanilla_items),
        })
    return rows


def analyze_pack(
    pack: str,
    configured: dict[str, dict],
    vanilla_setups: dict[str, list[str]],
    vanilla_items: dict[str, list[str]],
    bases: dict[str, dict],
) -> dict:
    setup_path = DLC_ROOT / pack / "WeaponData" / "WeaponGeneralSetupPrototypes.cfg"
    item_path = DLC_ROOT / pack / "ItemPrototypes.cfg"
    if not setup_path.exists():
        return {"pack": pack, "available": False, "reason": f"missing {setup_path.relative_to(PYTHON_ROOT)}", "weapons": []}

    local_setups = top_level_blocks(setup_path.read_text(encoding="utf-8", errors="replace"))
    local_items = top_level_blocks(item_path.read_text(encoding="utf-8", errors="replace")) if item_path.exists() else {}
    entries = []

    for setup_sid, block in sorted(local_setups.items()):
        if not setup_sid.startswith("Gun"):
            continue

        setup_base = resolve_setup_base(setup_sid, local_setups, vanilla_setups, configured)
        item_base = None if setup_base else resolve_dlc_item_base(setup_sid, local_items, vanilla_items, bases)
        linked = _linked_weapons(setup_sid, local_items, vanilla_items)

        if setup_base:
            weapon_class = setup_base["class"]
            family = setup_base["family"]
            base_setup = setup_base["general_setup_sid"]
            base_weapon = None
            resolution = "general_setup_inheritance"
            confidence = "structural"
        elif item_base:
            weapon_class = item_base["class"]
            family = item_base["family"]
            base_setup = _family_setup(configured, weapon_class, family)
            base_weapon = item_base["base_weapon_sid"]
            resolution = "item_prototype_inheritance"
            confidence = "structural"
        else:
            weapon_class = None
            family = None
            base_setup = None
            base_weapon = None
            resolution = "unresolved"
            confidence = "manual_review"

        entries.append({
            "content_pack": pack,
            "output_scope": f"DLCGameData/{pack}",
            "general_setup_sid": setup_sid,
            "direct_refkey": refkey(block),
            "direct_refurl": refurl(block),
            "general_setup_inheritance_chain": _combined_chain(setup_sid, local_setups, vanilla_setups),
            "linked_weapon_prototypes": linked,
            "class": weapon_class,
            "base_family": family,
            "base_general_setup_sid": base_setup,
            "base_weapon_sid": base_weapon,
            "resolution": resolution,
            "confidence": confidence,
            "vanilla_upgrade_prototype_count": len(direct_array_values(block, "UpgradePrototypeSIDs")),
            "source": str(setup_path.relative_to(PYTHON_ROOT)),
            "item_source": str(item_path.relative_to(PYTHON_ROOT)) if item_path.exists() else None,
        })

    return {
        "pack": pack,
        "available": True,
        "source": str(setup_path.relative_to(PYTHON_ROOT)),
        "item_source": str(item_path.relative_to(PYTHON_ROOT)) if item_path.exists() else None,
        "candidate_general_setups": len(entries),
        "resolved": sum(e["resolution"] != "unresolved" for e in entries),
        "unresolved": sum(e["resolution"] == "unresolved" for e in entries),
        "via_general_setup": sum(e["resolution"] == "general_setup_inheritance" for e in entries),
        "via_item_prototype": sum(e["resolution"] == "item_prototype_inheritance" for e in entries),
        "weapons": entries,
    }


def analyze() -> dict:
    configured = configured_weapons()
    bases = base_weapon_index(configured)
    vanilla_setups = top_level_blocks(VANILLA_SETUPS.read_text(encoding="utf-8", errors="replace"))
    vanilla_items = top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8", errors="replace"))

    packs = {
        pack: analyze_pack(pack, configured, vanilla_setups, vanilla_items, bases)
        for pack in EDITION_PACKS
    }
    entries = [entry for data in packs.values() for entry in data.get("weapons", [])]
    return {
        "summary": {
            "packs": len(EDITION_PACKS),
            "available_packs": sum(data.get("available", False) for data in packs.values()),
            "candidate_general_setups": len(entries),
            "resolved": sum(e["resolution"] != "unresolved" for e in entries),
            "unresolved": sum(e["resolution"] == "unresolved" for e in entries),
            "via_general_setup": sum(e["resolution"] == "general_setup_inheritance" for e in entries),
            "via_item_prototype": sum(e["resolution"] == "item_prototype_inheritance" for e in entries),
        },
        "notes": [
            "Read-only analysis; edition_weapons.json is never modified.",
            "Structural mappings are accepted only when GeneralSetup or ItemPrototype inheritance reaches a configured BPRUE base family.",
            "Inheritance chains combine the edition pack with BaseGame references.",
            "The game-facing scope remains DLCGameData/<pack>; Editions is only BPRUE's optional physical module root.",
        ],
        "packs": packs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Deluxe/PreOrder/Ultimate weapon inheritance for the optional BPRUE Editions module.")
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--details", action="store_true", help="Print inheritance evidence for every candidate.")
    args = parser.parse_args()

    report = analyze()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    s = report["summary"]
    print(
        f"Edition weapon analysis: packs={s['available_packs']}/{s['packs']} | "
        f"candidates={s['candidate_general_setups']} | resolved={s['resolved']} | "
        f"unresolved={s['unresolved']} | setup={s['via_general_setup']} | item={s['via_item_prototype']}"
    )
    for pack, data in report["packs"].items():
        if not data.get("available"):
            print(f"  {pack:<10} MISSING: {data['reason']}")
            continue
        print(
            f"  {pack:<10} candidates={data['candidate_general_setups']} | "
            f"resolved={data['resolved']} | unresolved={data['unresolved']} | "
            f"setup={data['via_general_setup']} | item={data['via_item_prototype']}"
        )
        if args.details:
            for entry in data["weapons"]:
                target = f"{entry['class']}/{entry['base_family']}" if entry["base_family"] else "UNRESOLVED"
                print(f"    {entry['general_setup_sid']} -> {target} [{entry['resolution']}]")
                print("      setup chain: " + " -> ".join(entry["general_setup_inheritance_chain"]))
                for weapon in entry["linked_weapon_prototypes"]:
                    print(f"      item: {weapon['weapon_sid']} -> " + " -> ".join(weapon["inheritance_chain"]))

    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
