from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from analysis_paths import UNIQUE_WEAPON_ANALYSIS, ensure_reports_dir

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
CFG_ROOT = PYTHON_ROOT / "CFGGenerators"
VANILLA_ROOT = PYTHON_ROOT / "VanillaReference"
WEAPON_PATH = VANILLA_ROOT / "WeaponPrototypes.cfg"
SETUP_PATH = VANILLA_ROOT / "WeaponGeneralSetupPrototypes.cfg"
UNIQUE_PATH = CFG_ROOT / "Common" / "unique_weapons.json"

CLASS_CONFIGS = {
    "AssaultRifles": CFG_ROOT / "AssaultRifles" / "assault_rifles_upgrades.json",
    "SMGs": CFG_ROOT / "SMGs" / "smg_upgrades.json",
    "Shotguns": CFG_ROOT / "Shotguns" / "shotgun_upgrades.json",
    "Pistols": CFG_ROOT / "Pistols" / "pistol_upgrades.json",
    "Snipers": CFG_ROOT / "Snipers" / "sniper_upgrades.json",
    "MachineGuns": CFG_ROOT / "MachineGuns" / "machine_gun_upgrades.json",
}

# Pure identity / plumbing fields are still kept in direct_overrides, but omitted
# from the compact signature_candidates list unless explicitly requested.
NOISE_FIELDS = {
    "SID", "LocalizationSID", "GeneralWeaponSetup", "UpgradePrototypeSIDs",
    "WeaponMesh", "ItemPrototypeSID", "Icon", "Icon1x1",
}


def top_level_blocks(text: str) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current: list[str] | None = None
    sid = ""
    depth = 0
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


def refkey(block: list[str] | None) -> str | None:
    if not block:
        return None
    match = re.search(r"(?:\{|;)refkey=([^;}]+)", block[0])
    return match.group(1).strip() if match else None


def direct_properties(block: list[str]) -> dict[str, object]:
    """Return direct scalar and struct-valued properties of one prototype block.

    Nested structs are preserved as normalized text. This deliberately avoids
    pretending we understand every GameData structure while still making Unique
    overrides such as fire modes, ammo mappings and attachment structures visible.
    """
    result: dict[str, object] = {}
    lines = block[1:-1]
    i = 0
    scalar = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$")
    struct_start = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*struct\.begin")
    while i < len(lines):
        line = lines[i]
        match = scalar.match(line)
        if match:
            result[match.group(1)] = match.group(2).strip()
            i += 1
            continue
        match = struct_start.match(line)
        if not match:
            i += 1
            continue
        name = match.group(1)
        nested = [line.strip()]
        depth = 1
        i += 1
        while i < len(lines) and depth:
            nested.append(lines[i].strip())
            if "struct.begin" in lines[i]:
                depth += 1
            if lines[i].strip() == "struct.end":
                depth -= 1
            i += 1
        result[name] = "\n".join(nested)
    return result


def inheritance_chain(sid: str, blocks: dict[str, list[str]]) -> list[str]:
    chain = [sid]
    seen = {sid}
    current = sid
    while current in blocks:
        parent = refkey(blocks[current])
        if not parent or parent in seen or parent.startswith("["):
            break
        chain.append(parent)
        seen.add(parent)
        current = parent
    return chain


def effective_properties(sid: str, blocks: dict[str, list[str]]) -> tuple[dict[str, object], list[str]]:
    chain = inheritance_chain(sid, blocks)
    result: dict[str, object] = {}
    for current in reversed(chain):
        block = blocks.get(current)
        if block:
            result.update(direct_properties(block))
    return result, chain


def diff_properties(base: dict[str, object], unique: dict[str, object]) -> dict[str, dict[str, object | None]]:
    result = {}
    for key in sorted(set(base) | set(unique)):
        before = base.get(key)
        after = unique.get(key)
        if before != after:
            result[key] = {"base": before, "unique": after}
    return result


def load_base_families() -> dict[tuple[str, str], dict]:
    result = {}
    for class_name, path in CLASS_CONFIGS.items():
        config = json.loads(path.read_text(encoding="utf-8"))
        for family_name, family in config.get("families", {}).items():
            result[(class_name, family_name)] = family
    return result


def weapon_users(blocks: dict[str, list[str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for sid, block in blocks.items():
        setup = direct_properties(block).get("GeneralWeaponSetup")
        if isinstance(setup, str):
            result[setup].append(sid)
    return {key: sorted(value) for key, value in result.items()}


def choose_unique_weapon(setup_sid: str, users: dict[str, list[str]]) -> str | None:
    candidates = users.get(setup_sid, [])
    return candidates[0] if len(candidates) == 1 else None


def analyze() -> dict:
    registry = json.loads(UNIQUE_PATH.read_text(encoding="utf-8"))
    base_families = load_base_families()
    weapon_blocks = top_level_blocks(WEAPON_PATH.read_text(encoding="utf-8"))
    setup_blocks = top_level_blocks(SETUP_PATH.read_text(encoding="utf-8"))
    users = weapon_users(weapon_blocks)

    entries = {}
    unresolved = []
    class_counts = Counter()

    for unique_name, unique in registry.get("uniques", {}).items():
        class_name = unique["class"]
        base_name = unique["base_family"]
        class_counts[class_name] += 1
        base = base_families.get((class_name, base_name))
        if not base:
            unresolved.append({"unique": unique_name, "reason": "base_family_not_found", "class": class_name, "base_family": base_name})
            continue

        unique_setup = unique["general_setup_sid"]
        base_setup = base.get("general_setup_sid")
        base_weapon = base.get("weapon_sid")
        unique_weapon = choose_unique_weapon(unique_setup, users)

        unique_setup_effective, unique_setup_chain = effective_properties(unique_setup, setup_blocks)
        base_setup_effective, base_setup_chain = effective_properties(base_setup, setup_blocks)
        setup_diff = diff_properties(base_setup_effective, unique_setup_effective)
        setup_direct = direct_properties(setup_blocks[unique_setup]) if unique_setup in setup_blocks else {}

        weapon_diff = {}
        weapon_direct = {}
        unique_weapon_chain: list[str] = []
        base_weapon_chain: list[str] = []
        if unique_weapon and base_weapon and unique_weapon in weapon_blocks and base_weapon in weapon_blocks:
            unique_weapon_effective, unique_weapon_chain = effective_properties(unique_weapon, weapon_blocks)
            base_weapon_effective, base_weapon_chain = effective_properties(base_weapon, weapon_blocks)
            weapon_diff = diff_properties(base_weapon_effective, unique_weapon_effective)
            weapon_direct = direct_properties(weapon_blocks[unique_weapon])

        candidate_fields = sorted(
            key for key in set(setup_diff) | set(weapon_diff)
            if key not in NOISE_FIELDS
        )

        entries[unique_name] = {
            "class": class_name,
            "base_family": base_name,
            "unique_general_setup_sid": unique_setup,
            "base_general_setup_sid": base_setup,
            "unique_weapon_sid": unique_weapon,
            "base_weapon_sid": base_weapon,
            "linked_weapon_candidates": users.get(unique_setup, []),
            "signature_candidate_fields": candidate_fields,
            "general_setup": {
                "inheritance_chain": unique_setup_chain,
                "base_inheritance_chain": base_setup_chain,
                "direct_overrides": setup_direct,
                "effective_diff_vs_base": setup_diff,
            },
            "weapon_prototype": {
                "inheritance_chain": unique_weapon_chain,
                "base_inheritance_chain": base_weapon_chain,
                "direct_overrides": weapon_direct,
                "effective_diff_vs_base": weapon_diff,
            },
        }

    return {
        "summary": {
            "registry_uniques": len(registry.get("uniques", {})),
            "analyzed": len(entries),
            "unresolved": len(unresolved),
            "by_class": dict(sorted(class_counts.items())),
        },
        "notes": [
            "effective_diff_vs_base resolves refkey inheritance before comparing values.",
            "Nested struct properties are intentionally preserved as normalized text rather than interpreted.",
            "signature_candidate_fields omits identity/plumbing fields and is a shortlist for manual signature design, not an automatic balance recommendation.",
            "If multiple WeaponPrototypes use one GeneralSetup, linked_weapon_candidates is populated and unique_weapon_sid remains null for manual review.",
        ],
        "unresolved": unresolved,
        "uniques": entries,
        "out_of_scope": registry.get("out_of_scope", {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Vanilla Unique weapons with their BPRUE base families.")
    parser.add_argument("--output", type=Path, default=UNIQUE_WEAPON_ANALYSIS)
    parser.add_argument("--print-details", action="store_true", help="Print each Unique's candidate fields after the summary.")
    args = parser.parse_args()

    report = analyze()
    ensure_reports_dir()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = report["summary"]
    print(
        f"Unique weapon analysis: registry={summary['registry_uniques']} | "
        f"analyzed={summary['analyzed']} | unresolved={summary['unresolved']}"
    )
    print("By class: " + ", ".join(f"{key}={value}" for key, value in summary["by_class"].items()))
    print(f"Report: {args.output}")

    if args.print_details:
        for name, entry in report["uniques"].items():
            fields = ", ".join(entry["signature_candidate_fields"]) or "(no non-plumbing differences)"
            print(f"{name:16} [{entry['class']}] <- {entry['base_family']}: {fields}")

    if report["unresolved"]:
        print("Unresolved:")
        for entry in report["unresolved"]:
            print(f"  - {entry['unique']}: {entry['reason']}")


if __name__ == "__main__":
    main()
