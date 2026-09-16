from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
CFG_ROOT = PYTHON_ROOT / "CFGGenerators"
VANILLA_WEAPONS = PYTHON_ROOT / "VanillaReference" / "WeaponPrototypes.cfg"
VANILLA_GENERAL_SETUPS = PYTHON_ROOT / "VanillaReference" / "WeaponGeneralSetupPrototypes.cfg"
REPORTS_DIR = SCRIPT_DIR / "Reports"
OUTPUT_PATH = REPORTS_DIR / "weapon_coverage.json"

CONFIGS = (
    CFG_ROOT / "AssaultRifles" / "assault_rifles_upgrades.json",
    CFG_ROOT / "SMGs" / "smg_upgrades.json",
    CFG_ROOT / "Shotguns" / "shotgun_upgrades.json",
    CFG_ROOT / "Pistols" / "pistol_upgrades.json",
    CFG_ROOT / "Snipers" / "sniper_upgrades.json",
    CFG_ROOT / "MachineGuns" / "machine_gun_upgrades.json",
)

# These are candidate signals, not a final truth table. The report deliberately
# keeps exclusions separate from suspected missing weapons so every excluded SID
# can be audited instead of silently disappearing from the diff.
UNIQUE_NAME_MARKERS = (
    "unique",
    "quest",
    "special",
    "prototype",
    "test",
    "debug",
)

WEAPON_CLASS_SUFFIXES = {
    "ST": "AssaultRifles",
    "PP": "SMGs",
    "HG": "Pistols",
    "SG": "Shotguns",
    "SP": "Snipers",
    "DMR": "Snipers",
    "MG": "MachineGuns",
}


def top_level_blocks(text: str) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current: list[str] | None = None
    depth = 0
    sid = ""
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if not line.startswith((" ", "\t")) and ": struct.begin" in stripped:
                sid = line.split(" :", 1)[0].strip()
                current = [line]
                depth = 1
            continue
        current.append(line)
        if "struct.begin" in stripped:
            depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0:
                blocks[sid] = current
                current = None
    return blocks


def direct_scalar(block: list[str], name: str) -> str | None:
    pattern = re.compile(rf"\s*{re.escape(name)}\s*=\s*(.+?)\s*$")
    depth = 0
    for line in block[1:-1]:
        stripped = line.strip()
        if "struct.begin" in stripped:
            depth += 1
            continue
        if stripped == "struct.end":
            depth -= 1
            continue
        if depth:
            continue
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return None


def refkey(block: list[str]) -> str | None:
    match = re.search(r"\{refkey=([^}]+)\}", block[0])
    return match.group(1).strip() if match else None


def configured_weapons() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in CONFIGS:
        if not path.exists():
            continue
        config = json.loads(path.read_text(encoding="utf-8"))
        weapon_class = path.parent.name
        for family_name, family in config.get("families", {}).items():
            weapon_sid = family.get("weapon_sid")
            setup_sid = family.get("general_setup_sid")
            if not weapon_sid and not setup_sid:
                continue
            key = setup_sid or weapon_sid
            result[key] = {
                "family": family_name,
                "class": weapon_class,
                "weapon_sid": weapon_sid,
                "general_setup_sid": setup_sid,
                "source": str(path.relative_to(PYTHON_ROOT)),
            }

        # Some older SMG caliber-only entries do not repeat weapon_sid. Keep
        # those visible as covered GeneralSetups without pretending they are a
        # separate Vanilla weapon prototype.
        if weapon_class == "SMGs":
            for family_name, family in config.get("caliber_families", {}).items():
                setup_sid = family.get("general_setup_sid")
                if setup_sid and setup_sid not in result:
                    result[setup_sid] = {
                        "family": family_name,
                        "class": weapon_class,
                        "weapon_sid": None,
                        "general_setup_sid": setup_sid,
                        "source": str(path.relative_to(PYTHON_ROOT)),
                        "caliber_only": True,
                    }
    return result


def class_from_sid(sid: str) -> str | None:
    parts = sid.split("_")
    for part in reversed(parts):
        if part in WEAPON_CLASS_SUFFIXES:
            return WEAPON_CLASS_SUFFIXES[part]
    return None


def looks_like_unique_or_internal(sid: str, block: list[str]) -> list[str]:
    reasons: list[str] = []
    lower_sid = sid.lower()
    for marker in UNIQUE_NAME_MARKERS:
        if marker in lower_sid:
            reasons.append(f"sid_marker:{marker}")

    # Unique/quest variants frequently inherit from another concrete Gun* SID.
    # This is intentionally a suspicion signal only; the report preserves the
    # candidate for review instead of automatically treating inheritance as
    # proof that it is unique.
    parent = refkey(block)
    if parent and parent.startswith("Gun") and parent != sid:
        reasons.append(f"inherits_weapon:{parent}")

    return reasons


def setup_candidates(setup_blocks: dict[str, list[str]]) -> set[str]:
    return {
        sid
        for sid in setup_blocks
        if sid.startswith("Gun") and class_from_sid(sid) is not None
    }


def build_report() -> dict:
    if not VANILLA_WEAPONS.exists():
        raise FileNotFoundError(VANILLA_WEAPONS)
    if not VANILLA_GENERAL_SETUPS.exists():
        raise FileNotFoundError(VANILLA_GENERAL_SETUPS)

    weapon_blocks = top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8"))
    setup_blocks = top_level_blocks(VANILLA_GENERAL_SETUPS.read_text(encoding="utf-8"))
    configured = configured_weapons()
    vanilla_setups = setup_candidates(setup_blocks)

    covered_setups = set(configured)
    covered_weapon_sids = {
        entry["weapon_sid"] for entry in configured.values() if entry.get("weapon_sid")
    }

    candidates = []
    excluded = []
    for setup_sid in sorted(vanilla_setups):
        if setup_sid in covered_setups:
            continue

        weapon_block = weapon_blocks.get(setup_sid)
        if weapon_block is None:
            candidates.append({
                "general_setup_sid": setup_sid,
                "weapon_sid": None,
                "class": class_from_sid(setup_sid),
                "status": "suspected_missing",
                "review_reasons": ["no_same_sid_weapon_prototype"],
            })
            continue

        exclusion_reasons = looks_like_unique_or_internal(setup_sid, weapon_block)
        entry = {
            "general_setup_sid": setup_sid,
            "weapon_sid": setup_sid,
            "class": class_from_sid(setup_sid),
            "parent_weapon_sid": refkey(weapon_block),
        }
        if exclusion_reasons:
            entry["status"] = "excluded_unique_or_variant_candidate"
            entry["exclusion_reasons"] = exclusion_reasons
            excluded.append(entry)
        else:
            entry["status"] = "suspected_missing"
            entry["review_reasons"] = ["vanilla_weapon_and_setup_not_covered_by_bprue"]
            candidates.append(entry)

    class_counts = Counter(entry["class"] or "Unknown" for entry in candidates)
    excluded_counts = Counter(entry["class"] or "Unknown" for entry in excluded)

    return {
        "sources": {
            "weapon_prototypes": str(VANILLA_WEAPONS.relative_to(PYTHON_ROOT)),
            "general_setups": str(VANILLA_GENERAL_SETUPS.relative_to(PYTHON_ROOT)),
            "bprue_configs": [str(path.relative_to(PYTHON_ROOT)) for path in CONFIGS if path.exists()],
        },
        "rules": {
            "candidate_scope": "Vanilla Gun* GeneralSetups whose SID identifies a supported weapon class.",
            "covered": "GeneralSetup SID is present in a BPRUE generator config.",
            "unique_filter": "Name markers and inheritance from another concrete Gun* prototype are exclusion signals; exclusions remain in the report for manual verification.",
            "suspected_missing": "Not covered by BPRUE and no current unique/internal exclusion signal. This is intentionally not equivalent to confirmed missing.",
        },
        "summary": {
            "vanilla_candidate_general_setups": len(vanilla_setups),
            "bprue_configured_general_setups": len(covered_setups),
            "bprue_configured_weapon_sids": len(covered_weapon_sids),
            "suspected_missing": len(candidates),
            "excluded_unique_or_variant_candidates": len(excluded),
            "suspected_missing_by_class": dict(sorted(class_counts.items())),
            "excluded_by_class": dict(sorted(excluded_counts.items())),
        },
        "bprue_covered": [configured[sid] for sid in sorted(configured)],
        "suspected_missing": candidates,
        "excluded_unique_or_variant_candidates": excluded,
    }


def print_report(report: dict, show_excluded: bool = False) -> None:
    summary = report["summary"]
    print(
        f"Vanilla candidates={summary['vanilla_candidate_general_setups']} | "
        f"BPRUE setups={summary['bprue_configured_general_setups']} | "
        f"suspected missing={summary['suspected_missing']} | "
        f"excluded/review={summary['excluded_unique_or_variant_candidates']}"
    )

    print("\nSuspected missing weapons:")
    if not report["suspected_missing"]:
        print("  <none>")
    for entry in report["suspected_missing"]:
        print(f"  [{entry['class'] or 'Unknown':<13}] {entry['general_setup_sid']}")

    if show_excluded:
        print("\nExcluded unique/variant candidates:")
        if not report["excluded_unique_or_variant_candidates"]:
            print("  <none>")
        for entry in report["excluded_unique_or_variant_candidates"]:
            reasons = ", ".join(entry["exclusion_reasons"])
            print(f"  [{entry['class'] or 'Unknown':<13}] {entry['general_setup_sid']} <- {reasons}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Vanilla weapon coverage with BPRUE while separating likely unique/special variants."
    )
    parser.add_argument("--show-excluded", action="store_true", help="Also print unique/variant exclusion candidates")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON report path")
    args = parser.parse_args()

    report = build_report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report, args.show_excluded)
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
