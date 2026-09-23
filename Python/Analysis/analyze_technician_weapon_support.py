from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = ANALYSIS_DIR.parent
COMMON = PYTHON_ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))

from generate_all_cfg import build_model
from technician_support import (
    vanilla_technician_upgrade_sids,
    vanilla_upgrade_general_setups,
    technician_upgrade_assignments,
)


def _weapon_label(setup_sid: str) -> str:
    for suffix in ("_SG", "_ST", "_PP"):
        if setup_sid.endswith(suffix):
            return setup_sid[:-len(suffix)]
    return setup_sid


def build_rows():
    model, _ = build_model(apply_layout=False)
    vanilla_by_tech = vanilla_technician_upgrade_sids()
    vanilla_upgrade_to_setups = vanilla_upgrade_general_setups()
    assignments = technician_upgrade_assignments(model)

    bprue_by_tech_setup = defaultdict(lambda: defaultdict(list))
    for tech_sid, upgrades in assignments.items():
        for upgrade in upgrades:
            for setup_sid in upgrade.general_setup_sids:
                bprue_by_tech_setup[tech_sid][setup_sid].append(upgrade.sid)

    rows = {}
    for tech_sid, vanilla_upgrade_sids in vanilla_by_tech.items():
        vanilla_by_setup = defaultdict(list)
        for upgrade_sid in vanilla_upgrade_sids:
            for setup_sid in vanilla_upgrade_to_setups.get(upgrade_sid, ()):
                vanilla_by_setup[setup_sid].append(upgrade_sid)

        all_setups = set(vanilla_by_setup) | set(bprue_by_tech_setup.get(tech_sid, {}))
        rows[tech_sid] = []
        for setup_sid in sorted(all_setups):
            vanilla_count = len(set(vanilla_by_setup.get(setup_sid, ())))
            bprue_count = len(set(bprue_by_tech_setup.get(tech_sid, {}).get(setup_sid, ())))
            rows[tech_sid].append((setup_sid, vanilla_count, bprue_count))
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Compare Vanilla technician weapon support with the BPRUE assignments derived from it."
    )
    parser.add_argument(
        "--tech",
        action="append",
        help="Only show technician SIDs containing this text (case-insensitive). Can be repeated.",
    )
    parser.add_argument(
        "--mismatches",
        action="store_true",
        help="Only show suspicious rows where Vanilla/BPRUE weapon coverage does not line up.",
    )
    args = parser.parse_args()

    rows = build_rows()
    filters = [value.lower() for value in (args.tech or [])]

    print("Vanilla technician weapon support vs BPRUE assignment")
    print("=" * 88)
    print("Counts are only a sanity check; this report intentionally does not list individual upgrades.")
    print()

    shown = 0
    suspicious = 0
    for tech_sid in sorted(rows):
        if filters and not any(value in tech_sid.lower() for value in filters):
            continue

        selected = []
        for setup_sid, vanilla_count, bprue_count in rows[tech_sid]:
            mismatch = (vanilla_count > 0) != (bprue_count > 0)
            if mismatch:
                suspicious += 1
            if args.mismatches and not mismatch:
                continue
            selected.append((setup_sid, vanilla_count, bprue_count, mismatch))

        if not selected:
            continue

        shown += 1
        print(tech_sid)
        for setup_sid, vanilla_count, bprue_count, mismatch in selected:
            state = "MISMATCH" if mismatch else "OK"
            print(
                f"  {_weapon_label(setup_sid):<30} "
                f"{setup_sid:<28} "
                f"Vanilla={'YES' if vanilla_count else 'no ':<3} ({vanilla_count:>2})  "
                f"BPRUE={'YES' if bprue_count else 'no ':<3} ({bprue_count:>2})  "
                f"{state}"
            )
        print()

    print("=" * 88)
    print(f"Technicians shown: {shown}")
    print(f"Coverage mismatches: {suspicious}")


if __name__ == "__main__":
    main()
