from __future__ import annotations

import argparse
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VANILLA_PATH = SCRIPT_DIR / "vanilla_upgrade_map.json"
BPRUE_PATH = SCRIPT_DIR / "bprue_upgrade_map.json"
OUTPUT_PATH = SCRIPT_DIR / "upgrade_map_comparison.json"


def load(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_slots(weapon: dict, modifications_only: bool = False) -> dict[tuple[str, int, str], list[dict]]:
    result: dict[tuple[str, int, str], list[dict]] = {}
    for target, columns in weapon.get("slots", {}).items():
        for column, verticals in columns.items():
            for vertical, upgrades in verticals.items():
                relevant = [u for u in upgrades if not modifications_only or u.get("is_modification") is True]
                if relevant:
                    result[(target, int(column), vertical)] = relevant
    return result


def occupied_columns(slots: dict[tuple[str, int, str], list[dict]]) -> set[tuple[str, int]]:
    return {(target, column) for target, column, _ in slots}


def build_comparison(vanilla: dict, bprue: dict) -> dict:
    weapons: dict[str, dict] = {}
    total_exact = 0
    total_column = 0

    for setup_sid, bprue_weapon in sorted(bprue["weapons"].items()):
        vanilla_weapon = vanilla["weapons"].get(setup_sid)
        if not vanilla_weapon:
            weapons[setup_sid] = {
                "status": "missing_vanilla_general_setup",
                "exact_slot_collisions": [],
                "shared_modification_columns": [],
            }
            continue

        # BPRUE upgrades are modifications. Vanilla stat upgrades (IsModification=false)
        # live in a separate UI/layout table and must not count as collisions.
        vanilla_slots = flatten_slots(vanilla_weapon, modifications_only=True)
        bprue_slots = flatten_slots(bprue_weapon, modifications_only=True)
        vanilla_columns = occupied_columns(vanilla_slots)
        bprue_columns = occupied_columns(bprue_slots)

        exact = []
        for key in sorted(set(vanilla_slots) & set(bprue_slots)):
            target, column, vertical = key
            exact.append({
                "target_part": target,
                "horizontal_position": column,
                "vertical_position": vertical,
                "vanilla_modification_sids": [u["sid"] for u in vanilla_slots[key]],
                "bprue_sids": [u["sid"] for u in bprue_slots[key]],
            })

        shared_columns = []
        for target, horizontal in sorted(vanilla_columns & bprue_columns):
            vanilla_here = {
                vertical: [u["sid"] for u in upgrades]
                for (slot_target, slot_horizontal, vertical), upgrades in vanilla_slots.items()
                if slot_target == target and slot_horizontal == horizontal
            }
            bprue_here = {
                vertical: [u["sid"] for u in upgrades]
                for (slot_target, slot_horizontal, vertical), upgrades in bprue_slots.items()
                if slot_target == target and slot_horizontal == horizontal
            }
            shared_columns.append({
                "target_part": target,
                "horizontal_position": horizontal,
                "vanilla_modifications": vanilla_here,
                "bprue": bprue_here,
                "has_exact_slot_collision": any(
                    (target, horizontal, vertical) in bprue_slots for vertical in vanilla_here
                ),
            })

        total_exact += len(exact)
        total_column += len(shared_columns)
        weapons[setup_sid] = {
            "status": "collision" if exact else "shared_column" if shared_columns else "clear",
            "vanilla_upgrade_count": vanilla_weapon.get("upgrade_count", 0),
            "vanilla_modification_count": sum(len(v) for v in vanilla_slots.values()),
            "bprue_upgrade_count": bprue_weapon.get("upgrade_count", 0),
            "exact_slot_collisions": exact,
            "shared_modification_columns": shared_columns,
        }

    return {
        "comparison_rule": "Only IsModification=true participates in Vanilla vs BPRUE layout collision checks.",
        "summary": {
            "bprue_general_setups": len(bprue["weapons"]),
            "general_setups_with_exact_collision": sum(1 for w in weapons.values() if w["status"] == "collision"),
            "general_setups_with_shared_column_only": sum(1 for w in weapons.values() if w["status"] == "shared_column"),
            "shared_modification_columns": total_column,
            "exact_slot_collisions": total_exact,
            "missing_vanilla_general_setups": sum(1 for w in weapons.values() if w["status"] == "missing_vanilla_general_setup"),
        },
        "weapons": weapons,
    }


def print_report(comparison: dict, only_weapon: str | None = None) -> None:
    summary = comparison["summary"]
    print(
        f"Compared {summary['bprue_general_setups']} BPRUE GeneralSetups against Vanilla IsModification=true only: "
        f"{summary['general_setups_with_exact_collision']} with exact collisions, "
        f"{summary['general_setups_with_shared_column_only']} with shared columns only, "
        f"{summary['shared_modification_columns']} shared modification columns, "
        f"{summary['exact_slot_collisions']} exact H/V collisions, "
        f"{summary['missing_vanilla_general_setups']} missing Vanilla setups."
    )

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
            target = overlap["target_part"]
            horizontal = overlap["horizontal_position"]
            marker = "COLLISION" if overlap["has_exact_slot_collision"] else "shared column"
            print(f"  {target} H={horizontal} [{marker}]")
            for vertical, sids in overlap["vanilla_modifications"].items():
                print(f"    Vanilla mod {vertical:<12} -> {', '.join(sids)}")
            for vertical, sids in overlap["bprue"].items():
                print(f"    BPRUE       {vertical:<12} -> {', '.join(sids)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Vanilla modification and generated BPRUE upgrade layout maps.")
    parser.add_argument("--weapon", help="Show one BPRUE GeneralSetup SID")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON comparison output")
    args = parser.parse_args()

    comparison = build_comparison(load(VANILLA_PATH), load(BPRUE_PATH))
    args.output.write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print_report(comparison, args.weapon)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
