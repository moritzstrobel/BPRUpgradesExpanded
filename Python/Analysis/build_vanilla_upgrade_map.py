from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
COMMON_DIR = PYTHON_ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(COMMON_DIR))

from vanilla_upgrade_layout import (  # noqa: E402
    VANILLA_GENERAL_SETUPS,
    VANILLA_UPGRADES,
    _direct_scalar,
    _sid,
    _top_level_blocks,
    vanilla_general_setup_upgrades,
)

OUTPUT_PATH = SCRIPT_DIR / "vanilla_upgrade_map.json"


def _enum_tail(value: str | None, default: str = "Unspecified") -> str:
    return value.rsplit("::", 1)[-1] if value else default


def parse_upgrade_layout() -> dict[str, dict[str, object]]:
    """Return layout-relevant fields for every vanilla upgrade prototype."""
    if not VANILLA_UPGRADES.exists():
        raise FileNotFoundError(VANILLA_UPGRADES)

    result: dict[str, dict[str, object]] = {}
    for block in _top_level_blocks(VANILLA_UPGRADES.read_text(encoding="utf-8")):
        sid = _sid(block)
        target = _direct_scalar(block, "UpgradeTargetPart")
        horizontal_raw = _direct_scalar(block, "HorizontalPosition")
        vertical = _direct_scalar(block, "VerticalPosition")
        is_modification = (_direct_scalar(block, "IsModification") or "false").lower() == "true"

        if not target:
            continue

        horizontal = int(horizontal_raw) if horizontal_raw and re.fullmatch(r"-?\d+", horizontal_raw) else 0
        result[sid] = {
            "target_part": _enum_tail(target),
            "horizontal_position": horizontal,
            "horizontal_explicit": horizontal_raw is not None,
            "vertical_position": _enum_tail(vertical),
            "vertical_explicit": vertical is not None,
            "is_modification": is_modification,
        }
    return result


def build_map() -> dict[str, object]:
    """Build GeneralSetup -> slot -> column -> vertical-position -> upgrade map."""
    setup_upgrades = vanilla_general_setup_upgrades()
    layouts = parse_upgrade_layout()

    weapons: dict[str, object] = {}
    unresolved: dict[str, list[str]] = {}

    for setup_sid, upgrade_sids in sorted(setup_upgrades.items()):
        slots: defaultdict[str, defaultdict[int, defaultdict[str, list[dict[str, object]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        missing: list[str] = []

        for upgrade_sid in upgrade_sids:
            layout = layouts.get(upgrade_sid)
            if not layout:
                missing.append(upgrade_sid)
                continue

            slots[str(layout["target_part"])][int(layout["horizontal_position"])][str(layout["vertical_position"])].append(
                {
                    "sid": upgrade_sid,
                    "is_modification": layout["is_modification"],
                    "horizontal_explicit": layout["horizontal_explicit"],
                    "vertical_explicit": layout["vertical_explicit"],
                }
            )

        weapons[setup_sid] = {
            "upgrade_count": len(upgrade_sids),
            "slots": {
                target: {
                    str(column): dict(sorted(verticals.items()))
                    for column, verticals in sorted(columns.items())
                }
                for target, columns in sorted(slots.items())
            },
        }
        if missing:
            unresolved[setup_sid] = missing

    return {
        "sources": {
            "upgrade_prototypes": str(VANILLA_UPGRADES.relative_to(PYTHON_ROOT)),
            "general_setups": str(VANILLA_GENERAL_SETUPS.relative_to(PYTHON_ROOT)),
        },
        "weapon_count": len(weapons),
        "weapons": weapons,
        "unresolved_upgrade_sids": unresolved,
    }


def print_weapon(data: dict[str, object], setup_sid: str) -> None:
    weapon = data["weapons"].get(setup_sid)
    if not weapon:
        raise SystemExit(f"Unknown GeneralSetup SID: {setup_sid}")

    print(f"{setup_sid} ({weapon['upgrade_count']} vanilla upgrades)")
    slots = weapon["slots"]
    if not slots:
        print("  <no layout-capable upgrades>")
        return

    for target, columns in slots.items():
        print(f"  {target}")
        for column, verticals in columns.items():
            print(f"    H={column}")
            for vertical, upgrades in verticals.items():
                label = vertical if vertical != "Unspecified" else "<no VerticalPosition>"
                for upgrade in upgrades:
                    flags = []
                    if upgrade["is_modification"]:
                        flags.append("modification")
                    if not upgrade["horizontal_explicit"]:
                        flags.append("H implicit=0")
                    if not upgrade["vertical_explicit"]:
                        flags.append("V implicit")
                    suffix = f" [{', '.join(flags)}]" if flags else ""
                    print(f"      {label:<24} -> {upgrade['sid']}{suffix}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a vanilla STALKER 2 weapon-upgrade slot/layout map.")
    parser.add_argument("--weapon", help="Print one GeneralSetup SID, e.g. GunAK74_ST")
    parser.add_argument("--all", action="store_true", help="Print every GeneralSetup to the console")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON output path")
    args = parser.parse_args()

    data = build_map()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Built vanilla upgrade map for {data['weapon_count']} GeneralSetups")
    print(f"Wrote {args.output}")

    if data["unresolved_upgrade_sids"]:
        count = sum(len(values) for values in data["unresolved_upgrade_sids"].values())
        print(f"Warning: {count} referenced UpgradePrototypeSIDs have no layout-capable prototype block")

    if args.weapon:
        print()
        print_weapon(data, args.weapon)
    elif args.all:
        for setup_sid in data["weapons"]:
            print()
            print_weapon(data, setup_sid)


if __name__ == "__main__":
    main()
