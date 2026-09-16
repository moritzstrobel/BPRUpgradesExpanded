from __future__ import annotations

import json
import sys
from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = ANALYSIS_DIR.parent
COMMON = PYTHON_ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))

from analysis_paths import TECHNICIAN_UPGRADE_MAP, ensure_reports_dir
from generate_all_cfg import build_model
from technician_support import (
    technician_upgrade_assignments,
    vanilla_technician_general_setups,
    vanilla_technician_upgrade_sids,
)


def build_report() -> dict:
    model, _configs = build_model(apply_layout=False)
    assignments = technician_upgrade_assignments(model)
    vanilla_upgrades = vanilla_technician_upgrade_sids()
    vanilla_setups = vanilla_technician_general_setups()

    candidate_upgrades = model.technician_upgrades()
    candidate_sids = {upgrade.sid for upgrade in candidate_upgrades}
    assigned_sids = {
        upgrade.sid
        for upgrades in assignments.values()
        for upgrade in upgrades
    }
    candidate_setups = {
        setup_sid
        for upgrade in candidate_upgrades
        for setup_sid in upgrade.general_setup_sids
    }
    supported_setups = set().union(*vanilla_setups.values()) if vanilla_setups else set()

    technicians = {}
    for technician_sid in sorted(assignments):
        upgrades = assignments[technician_sid]
        setups = sorted(vanilla_setups.get(technician_sid, ()))
        technicians[technician_sid] = {
            "vanilla_upgrade_count": len(vanilla_upgrades.get(technician_sid, ())),
            "vanilla_weapon_setup_count": len(setups),
            "vanilla_weapon_setups": setups,
            "bprue_upgrade_count": len(upgrades),
            "bprue_upgrade_sids": [upgrade.sid for upgrade in upgrades],
        }

    return {
        "summary": {
            "technician_count": len(assignments),
            "bprue_technician_upgrade_count": len(candidate_upgrades),
            "assigned_bprue_upgrade_count": len(assigned_sids),
            "unassigned_bprue_upgrade_count": len(candidate_sids - assigned_sids),
            "bprue_weapon_setup_count": len(candidate_setups),
            "unsupported_bprue_weapon_setup_count": len(candidate_setups - supported_setups),
        },
        "unassigned_bprue_upgrade_sids": sorted(candidate_sids - assigned_sids),
        "unsupported_bprue_weapon_setups": sorted(candidate_setups - supported_setups),
        "technicians": technicians,
    }


def print_summary(report: dict) -> None:
    summary = report["summary"]
    print("Technician support audit")
    print("=" * 80)
    for technician_sid, data in report["technicians"].items():
        print(
            f"{technician_sid:<32} "
            f"Vanilla upgrades={data['vanilla_upgrade_count']:>4} | "
            f"weapon setups={data['vanilla_weapon_setup_count']:>3} | "
            f"BPRUE upgrades={data['bprue_upgrade_count']:>4}"
        )
    print("=" * 80)
    print(
        f"Technicians={summary['technician_count']} | "
        f"BPRUE upgrades={summary['bprue_technician_upgrade_count']} | "
        f"assigned={summary['assigned_bprue_upgrade_count']} | "
        f"unassigned={summary['unassigned_bprue_upgrade_count']}"
    )
    print(
        f"BPRUE weapon setups={summary['bprue_weapon_setup_count']} | "
        f"unsupported setups={summary['unsupported_bprue_weapon_setup_count']}"
    )
    if report["unsupported_bprue_weapon_setups"]:
        print("Unsupported BPRUE weapon setups:")
        for sid in report["unsupported_bprue_weapon_setups"]:
            print(f"  - {sid}")


def main() -> None:
    report = build_report()
    ensure_reports_dir()
    TECHNICIAN_UPGRADE_MAP.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_summary(report)
    print(f"Report: {TECHNICIAN_UPGRADE_MAP}")


if __name__ == "__main__":
    main()
