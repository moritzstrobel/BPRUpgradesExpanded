from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PYTHON_ROOT))

from analysis_paths import BPRUE_UPGRADE_MAP, ensure_reports_dir  # noqa: E402
from generate_all_cfg import build_model  # noqa: E402

OUTPUT_PATH = BPRUE_UPGRADE_MAP


def build_map() -> dict[str, object]:
    """Build the same setup -> slot -> column -> vertical map for generated BPRUE upgrades."""
    model, _ = build_model()
    setups: defaultdict[str, list] = defaultdict(list)
    for upgrade in model.upgrades:
        for setup_sid in upgrade.general_setup_sids:
            setups[setup_sid].append(upgrade)

    weapons: dict[str, object] = {}
    for setup_sid, upgrades in sorted(setups.items()):
        slots: defaultdict[str, defaultdict[int, defaultdict[str, list[dict[str, object]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        for upgrade in upgrades:
            horizontal = upgrade.horizontal_position if upgrade.horizontal_position is not None else 0
            vertical = upgrade.vertical_position or "Unspecified"
            slots[upgrade.target_part][horizontal][vertical].append({
                "sid": upgrade.sid,
                "class": upgrade.weapon_class,
                "group": upgrade.group,
                "is_modification": True,
                "horizontal_explicit": upgrade.horizontal_position is not None,
                "vertical_explicit": upgrade.vertical_position is not None,
                "blocking_sids": list(upgrade.blocking_sids),
            })
        weapons[setup_sid] = {
            "upgrade_count": len(upgrades),
            "slots": {
                target: {str(column): dict(sorted(verticals.items())) for column, verticals in sorted(columns.items())}
                for target, columns in sorted(slots.items())
            },
        }
    return {
        "source": "unified UpgradeBuildModel after apply_layout_to_model()",
        "weapon_count": len(weapons),
        "upgrade_count": len(model.upgrades),
        "weapons": weapons,
    }


def print_weapon(data: dict[str, object], setup_sid: str) -> None:
    weapon = data["weapons"].get(setup_sid)
    if not weapon:
        raise SystemExit(f"Unknown GeneralSetup SID: {setup_sid}")
    print(f"{setup_sid} ({weapon['upgrade_count']} BPRUE upgrades)")
    for target, columns in weapon["slots"].items():
        print(f"  {target}")
        for column, verticals in columns.items():
            print(f"    H={column}")
            for vertical, upgrades in verticals.items():
                label = vertical if vertical != "Unspecified" else "<no VerticalPosition>"
                for upgrade in upgrades:
                    flags = [upgrade["class"], upgrade["group"]]
                    if not upgrade["horizontal_explicit"]:
                        flags.append("H implicit=0")
                    if not upgrade["vertical_explicit"]:
                        flags.append("V implicit")
                    print(f"      {label:<24} -> {upgrade['sid']} [{', '.join(flags)}]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the generated BPRUE weapon-upgrade slot/layout map.")
    parser.add_argument("--weapon", help="Print one GeneralSetup SID")
    parser.add_argument("--all", action="store_true", help="Print every BPRUE GeneralSetup")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON output path")
    args = parser.parse_args()
    data = build_map()
    ensure_reports_dir()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Built BPRUE upgrade map for {data['weapon_count']} GeneralSetups / {data['upgrade_count']} upgrades")
    print(f"Wrote {args.output}")
    if args.weapon:
        print()
        print_weapon(data, args.weapon)
    elif args.all:
        for setup_sid in data["weapons"]:
            print()
            print_weapon(data, setup_sid)


if __name__ == "__main__":
    main()
