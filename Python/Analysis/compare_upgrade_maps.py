from __future__ import annotations

import argparse
import json
from pathlib import Path

from analysis_paths import BPRUE_UPGRADE_MAP, UPGRADE_MAP_COMPARISON, VANILLA_UPGRADE_MAP, ensure_reports_dir

VANILLA_PATH = VANILLA_UPGRADE_MAP
BPRUE_PATH = BPRUE_UPGRADE_MAP
OUTPUT_PATH = UPGRADE_MAP_COMPARISON


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_slots(weapon: dict, modifications_only: bool = False) -> dict[tuple[str, int, str], list[dict]]:
    result = {}
    for target, columns in weapon.get("slots", {}).items():
        for column, verticals in columns.items():
            for vertical, upgrades in verticals.items():
                relevant = [u for u in upgrades if not modifications_only or u.get("is_modification") is True]
                if relevant:
                    result[(target, int(column), vertical)] = relevant
    return result


def occupied_columns(slots: dict) -> set[tuple[str, int]]:
    return {(target, column) for target, column, _ in slots}


def build_comparison(vanilla: dict, bprue: dict) -> dict:
    weapons = {}
    total_exact = total_column = 0
    for setup_sid, bprue_weapon in sorted(bprue["weapons"].items()):
        vanilla_weapon = vanilla["weapons"].get(setup_sid)
        if not vanilla_weapon:
            weapons[setup_sid] = {"status": "missing_vanilla_general_setup", "exact_slot_collisions": [], "shared_modification_columns": []}
            continue
        vanilla_slots = flatten_slots(vanilla_weapon, modifications_only=True)
        bprue_slots = flatten_slots(bprue_weapon, modifications_only=True)
        vanilla_columns = occupied_columns(vanilla_slots)
        bprue_columns = occupied_columns(bprue_slots)
        exact = []
        for key in sorted(set(vanilla_slots) & set(bprue_slots)):
            target, column, vertical = key
            exact.append({"target_part": target, "horizontal_position": column, "vertical_position": vertical,
                          "vanilla_modification_sids": [u["sid"] for u in vanilla_slots[key]],
                          "bprue_sids": [u["sid"] for u in bprue_slots[key]]})
        shared_columns = []
        for target, horizontal in sorted(vanilla_columns & bprue_columns):
            vanilla_here = {vertical: [u["sid"] for u in upgrades] for (t, h, vertical), upgrades in vanilla_slots.items() if t == target and h == horizontal}
            bprue_here = {vertical: [u["sid"] for u in upgrades] for (t, h, vertical), upgrades in bprue_slots.items() if t == target and h == horizontal}
            shared_columns.append({"target_part": target, "horizontal_position": horizontal,
                                   "vanilla_modifications": vanilla_here, "bprue": bprue_here,
                                   "has_exact_slot_collision": any((target, horizontal, vertical) in bprue_slots for vertical in vanilla_here)})
        total_exact += len(exact)
        total_column += len(shared_columns)
        weapons[setup_sid] = {"status": "collision" if exact else "shared_column" if shared_columns else "clear",
                              "vanilla_upgrade_count": vanilla_weapon.get("upgrade_count", 0),
                              "vanilla_modification_count": sum(len(v) for v in vanilla_slots.values()),
                              "bprue_upgrade_count": bprue_weapon.get("upgrade_count", 0),
                              "exact_slot_collisions": exact, "shared_modification_columns": shared_columns}
    return {"comparison_rule": "Only IsModification=true participates in Vanilla vs BPRUE layout collision checks.",
            "summary": {"bprue_general_setups": len(bprue["weapons"]),
                        "general_setups_with_exact_collision": sum(w["status"] == "collision" for w in weapons.values()),
                        "general_setups_with_shared_column_only": sum(w["status"] == "shared_column" for w in weapons.values()),
                        "shared_modification_columns": total_column, "exact_slot_collisions": total_exact,
                        "missing_vanilla_general_setups": sum(w["status"] == "missing_vanilla_general_setup" for w in weapons.values())},
            "weapons": weapons}


def print_report(comparison: dict, only_weapon: str | None = None) -> None:
    summary = comparison["summary"]
    print(f"Compared {summary['bprue_general_setups']} BPRUE GeneralSetups against Vanilla IsModification=true only: "
          f"{summary['general_setups_with_exact_collision']} with exact collisions, "
          f"{summary['general_setups_with_shared_column_only']} with shared columns only, "
          f"{summary['shared_modification_columns']} shared modification columns, "
          f"{summary['exact_slot_collisions']} exact H/V collisions, "
          f"{summary['missing_vanilla_general_setups']} missing Vanilla setups.")
    items = comparison["weapons"].items()
    if only_weapon:
        weapon = comparison["weapons"].get(only_weapon)
        if weapon is None:
            raise SystemExit(f"Unknown BPRUE GeneralSetup SID: {only_weapon}")
        items = [(only_weapon, weapon)]
    for setup_sid, weapon in items:
        if weapon["status"] == "clear" and not only_weapon:
            continue
        print(f"\n{setup_sid}: {weapon['status']}")
        if weapon["status"] == "missing_vanilla_general_setup":
            continue
        for overlap in weapon["shared_modification_columns"]:
            marker = "COLLISION" if overlap["has_exact_slot_collision"] else "shared column"
            print(f"  {overlap['target_part']} H={overlap['horizontal_position']} [{marker}]")
            for vertical, sids in overlap["vanilla_modifications"].items():
                print(f"    Vanilla mod {vertical:<12} -> {', '.join(sids)}")
            for vertical, sids in overlap["bprue"].items():
                print(f"    BPRUE       {vertical:<12} -> {', '.join(sids)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Vanilla modification and generated BPRUE upgrade layout maps.")
    parser.add_argument("--weapon", help="Show one BPRUE GeneralSetup SID")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON comparison output")
    args = parser.parse_args()
    ensure_reports_dir()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    comparison = build_comparison(load(VANILLA_PATH), load(BPRUE_PATH))
    args.output.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print_report(comparison, args.weapon)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
