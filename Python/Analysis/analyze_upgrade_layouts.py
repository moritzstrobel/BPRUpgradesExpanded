from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from analysis_paths import BPRUE_UPGRADE_MAP, UPGRADE_LAYOUT_ANALYSIS, VANILLA_UPGRADE_MAP, ensure_reports_dir

VANILLA_PATH = VANILLA_UPGRADE_MAP
BPRUE_PATH = BPRUE_UPGRADE_MAP
OUTPUT_PATH = UPGRADE_LAYOUT_ANALYSIS


def load(path: Path) -> dict:
    if not path.exists(): raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def modification_columns(weapon: dict) -> dict[str, dict[int, list[dict]]]:
    result = defaultdict(lambda: defaultdict(list))
    for target, columns in weapon.get("slots", {}).items():
        for column, verticals in columns.items():
            for vertical, upgrades in verticals.items():
                for upgrade in upgrades:
                    if upgrade.get("is_modification") is True: result[target][int(column)].append({"vertical": vertical, **upgrade})
    return {target: dict(columns) for target, columns in result.items()}


def all_columns(weapon: dict) -> dict[str, set[int]]:
    return {target: {int(column) for column in columns} for target, columns in weapon.get("slots", {}).items()}


def bprue_columns(weapon: dict) -> dict[str, dict[int, list[dict]]]:
    result = defaultdict(lambda: defaultdict(list))
    for target, columns in weapon.get("slots", {}).items():
        for column, verticals in columns.items():
            for vertical, upgrades in verticals.items():
                for upgrade in upgrades: result[target][int(column)].append({"vertical": vertical, **upgrade})
    return {target: dict(columns) for target, columns in result.items()}


def analyze_weapon(vanilla_weapon: dict, bprue_weapon: dict) -> dict:
    vanilla_mods = modification_columns(vanilla_weapon); vanilla_any = all_columns(vanilla_weapon); generated = bprue_columns(bprue_weapon)
    targets = sorted(set(vanilla_any) | set(vanilla_mods) | set(generated)); target_analysis = {}
    for target in targets:
        vanilla_mod_columns = sorted(vanilla_mods.get(target, {})); generated_columns = sorted(generated.get(target, {})); vanilla_all_columns = sorted(vanilla_any.get(target, set()))
        vanilla_max_mod = max(vanilla_mod_columns) if vanilla_mod_columns else None; generated_min = min(generated_columns) if generated_columns else None
        gap = generated_min - vanilla_max_mod - 1 if generated_min is not None and vanilla_max_mod is not None else None
        generated_details = []
        for column in generated_columns:
            upgrades = generated[target][column]; verticals = [u["vertical"] for u in upgrades]; groups = sorted({str(u.get("group", "")) for u in upgrades if u.get("group")})
            generated_details.append({"horizontal_position": column, "upgrade_count": len(upgrades), "vertical_positions": verticals, "groups": groups,
                                      "has_top": "Top" in verticals, "has_down": "Down" in verticals, "has_unspecified": "Unspecified" in verticals,
                                      "sids": [u["sid"] for u in upgrades]})
        target_analysis[target] = {"vanilla_has_target": target in vanilla_any, "vanilla_has_modifications": bool(vanilla_mod_columns),
                                   "vanilla_all_columns": vanilla_all_columns, "vanilla_modification_columns": vanilla_mod_columns,
                                   "vanilla_max_modification_column": vanilla_max_mod, "bprue_columns": generated_columns, "bprue_first_column": generated_min,
                                   "gap_after_last_vanilla_modification": gap, "bprue_column_count": len(generated_columns),
                                   "bprue_upgrade_count": sum(len(v) for v in generated.get(target, {}).values()), "bprue_columns_detail": generated_details}
    anomalies = []
    for target, data in target_analysis.items():
        if not data["bprue_columns"]: continue
        if not data["vanilla_has_target"]: anomalies.append({"type": "new_target_part", "target_part": target})
        if not data["vanilla_has_modifications"]: anomalies.append({"type": "no_vanilla_modification_table", "target_part": target})
        gap = data["gap_after_last_vanilla_modification"]
        if gap is not None and gap > 0: anomalies.append({"type": "gap_after_vanilla_modifications", "target_part": target, "columns": gap})
        columns = data["bprue_columns"]
        if columns and columns != list(range(columns[0], columns[-1] + 1)): anomalies.append({"type": "non_contiguous_bprue_columns", "target_part": target, "columns": columns})
        for column in data["bprue_columns_detail"]:
            if column["upgrade_count"] > 2: anomalies.append({"type": "more_than_two_variants_in_column", "target_part": target,
                                                               "horizontal_position": column["horizontal_position"], "upgrade_count": column["upgrade_count"],
                                                               "vertical_positions": column["vertical_positions"], "groups": column["groups"]})
    return {"vanilla_upgrade_count": vanilla_weapon.get("upgrade_count", 0), "bprue_upgrade_count": bprue_weapon.get("upgrade_count", 0),
            "targets": target_analysis, "anomalies": anomalies}


def build_analysis(vanilla: dict, bprue: dict) -> dict:
    weapons = {}; anomaly_counts = defaultdict(int); missing = []
    for setup_sid, bprue_weapon in sorted(bprue["weapons"].items()):
        vanilla_weapon = vanilla["weapons"].get(setup_sid)
        if vanilla_weapon is None: missing.append(setup_sid); continue
        analysis = analyze_weapon(vanilla_weapon, bprue_weapon); weapons[setup_sid] = analysis
        for anomaly in analysis["anomalies"]: anomaly_counts[anomaly["type"]] += 1
    return {"summary": {"analyzed_general_setups": len(weapons), "missing_vanilla_general_setups": missing,
                        "anomaly_counts": dict(sorted(anomaly_counts.items()))}, "weapons": weapons}


def print_weapon(setup_sid: str, weapon: dict) -> None:
    print(f"\n{setup_sid}: Vanilla={weapon['vanilla_upgrade_count']} / BPRUE={weapon['bprue_upgrade_count']}")
    for target, data in weapon["targets"].items():
        if not data["bprue_columns"]: continue
        print(f"  {target:<12} Vanilla mods={(data['vanilla_modification_columns'] or 'none')!s:<12} BPRUE={data['bprue_columns']!s:<16} gap={data['gap_after_last_vanilla_modification']}")
        for column in data["bprue_columns_detail"]:
            print(f"    H={column['horizontal_position']}: {column['groups']} -> {column['vertical_positions']} ({column['upgrade_count']} upgrades)")
    for anomaly in weapon["anomalies"]: print(f"  ! {anomaly['type']}: {json.dumps(anomaly, ensure_ascii=False)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze structural differences between Vanilla and BPRUE modification layouts.")
    parser.add_argument("--weapon", help="Print one GeneralSetup SID"); parser.add_argument("--all", action="store_true", help="Print all analyzed weapons")
    parser.add_argument("--anomalies", action="store_true", help="Print only weapons with structural anomalies"); parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON output path")
    args = parser.parse_args(); ensure_reports_dir(); args.output.parent.mkdir(parents=True, exist_ok=True)
    analysis = build_analysis(load(VANILLA_PATH), load(BPRUE_PATH)); args.output.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    summary = analysis["summary"]; print(f"Analyzed {summary['analyzed_general_setups']} BPRUE GeneralSetups"); print(f"Anomalies: {summary['anomaly_counts'] or 'none'}")
    if summary["missing_vanilla_general_setups"]: print(f"Missing Vanilla setups: {', '.join(summary['missing_vanilla_general_setups'])}")
    if args.weapon:
        weapon = analysis["weapons"].get(args.weapon)
        if weapon is None: raise SystemExit(f"Unknown analyzed GeneralSetup SID: {args.weapon}")
        print_weapon(args.weapon, weapon)
    elif args.all:
        for setup_sid, weapon in analysis["weapons"].items(): print_weapon(setup_sid, weapon)
    elif args.anomalies:
        for setup_sid, weapon in analysis["weapons"].items():
            if weapon["anomalies"]: print_weapon(setup_sid, weapon)
    print(f"\nWrote {args.output}")


if __name__ == "__main__": main()
