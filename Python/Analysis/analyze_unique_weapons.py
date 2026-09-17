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

NOISE_FIELDS = {
    "SID", "LocalizationSID", "GeneralWeaponSetup", "UpgradePrototypeSIDs",
    "WeaponMesh", "ItemPrototypeSID", "Icon", "Icon1x1",
}

SCALAR_RE = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*|\[\d+\])\s*=\s*(.+?)\s*$")
STRUCT_RE = re.compile(r"\s*([A-Za-z_][A-Za-z0-9_]*|\[\d+\])\s*:\s*struct\.begin")
NUMBER_RE = re.compile(r"^([+-]?(?:\d+(?:\.\d*)?|\.\d+))(%?)$")


def top_level_blocks(text: str) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}
    current: list[str] | None = None
    sid = ""
    depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if not line.startswith((" ", "\t")) and ": struct.begin" in stripped:
                sid = line.split(" :", 1)[0].strip(); current = [line]; depth = 1
            continue
        current.append(line)
        if "struct.begin" in stripped: depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0:
                blocks[sid] = current; current = None
    return blocks


def refkey(block: list[str] | None) -> str | None:
    if not block: return None
    match = re.search(r"(?:\{|;)refkey=([^;}]+)", block[0])
    return match.group(1).strip() if match else None


def parse_struct_lines(lines: list[str], start: int = 0, stop_at_end: bool = False) -> tuple[dict[str, object], int]:
    """Parse GameData scalar/struct properties into nested dictionaries.

    This is intentionally structural rather than schema-aware. Numeric array keys
    such as [0] are retained so FireTypes, recoil structures and similar nested
    values can be compared leaf-by-leaf without guessing their meaning.
    """
    result: dict[str, object] = {}
    i = start
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped == "struct.end" and stop_at_end:
            return result, i + 1
        struct_match = STRUCT_RE.match(lines[i])
        if struct_match:
            child, i = parse_struct_lines(lines, i + 1, True)
            result[struct_match.group(1)] = child
            continue
        scalar_match = SCALAR_RE.match(lines[i])
        if scalar_match:
            result[scalar_match.group(1)] = scalar_match.group(2).strip()
        i += 1
    return result, i


def direct_properties(block: list[str]) -> dict[str, object]:
    result, _ = parse_struct_lines(block[1:-1])
    return result


def inheritance_chain(sid: str, blocks: dict[str, list[str]]) -> list[str]:
    chain = [sid]; seen = {sid}; current = sid
    while current in blocks:
        parent = refkey(blocks[current])
        if not parent or parent in seen or parent.startswith("["): break
        chain.append(parent); seen.add(parent); current = parent
    return chain


def deep_merge(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)  # type: ignore[arg-type]
        else:
            result[key] = value
    return result


def effective_properties(sid: str, blocks: dict[str, list[str]]) -> tuple[dict[str, object], list[str]]:
    chain = inheritance_chain(sid, blocks)
    result: dict[str, object] = {}
    for current in reversed(chain):
        block = blocks.get(current)
        if block: result = deep_merge(result, direct_properties(block))
    return result, chain


def numeric_delta(before: object, after: object) -> dict[str, float] | None:
    if not isinstance(before, str) or not isinstance(after, str): return None
    left = NUMBER_RE.match(before); right = NUMBER_RE.match(after)
    if not left or not right or left.group(2) != right.group(2): return None
    base = float(left.group(1)); unique = float(right.group(1))
    result = {"absolute": unique - base}
    if base != 0: result["percent"] = ((unique - base) / abs(base)) * 100.0
    return result


def leaf_diff(base: object, unique: object, path: str = "") -> list[dict[str, object]]:
    if isinstance(base, dict) and isinstance(unique, dict):
        result: list[dict[str, object]] = []
        for key in sorted(set(base) | set(unique)):
            child_path = f"{path}.{key}" if path else key
            if key not in base:
                result.append({"path": child_path, "base": None, "unique": unique[key], "change": "added"})
            elif key not in unique:
                result.append({"path": child_path, "base": base[key], "unique": None, "change": "removed"})
            else:
                result.extend(leaf_diff(base[key], unique[key], child_path))
        return result
    if base == unique: return []
    entry: dict[str, object] = {"path": path, "base": base, "unique": unique, "change": "changed"}
    delta = numeric_delta(base, unique)
    if delta is not None: entry["numeric_delta"] = delta
    return [entry]


def top_level_diff(base: dict[str, object], unique: dict[str, object]) -> dict[str, dict[str, object | None]]:
    result = {}
    for key in sorted(set(base) | set(unique)):
        before = base.get(key); after = unique.get(key)
        if before != after: result[key] = {"base": before, "unique": after}
    return result


def load_base_families() -> dict[tuple[str, str], dict]:
    result = {}
    for class_name, path in CLASS_CONFIGS.items():
        config = json.loads(path.read_text(encoding="utf-8"))
        for family_name, family in config.get("families", {}).items(): result[(class_name, family_name)] = family
    return result


def weapon_users(blocks: dict[str, list[str]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for sid, block in blocks.items():
        setup = direct_properties(block).get("GeneralWeaponSetup")
        if isinstance(setup, str): result[setup].append(sid)
    return {key: sorted(value) for key, value in result.items()}


def choose_unique_weapon(setup_sid: str, users: dict[str, list[str]]) -> str | None:
    candidates = users.get(setup_sid, [])
    return candidates[0] if len(candidates) == 1 else None


def filtered_leaf_diffs(diffs: list[dict[str, object]]) -> list[dict[str, object]]:
    return [entry for entry in diffs if str(entry["path"]).split(".", 1)[0] not in NOISE_FIELDS]


def analyze() -> dict:
    registry = json.loads(UNIQUE_PATH.read_text(encoding="utf-8"))
    base_families = load_base_families()
    weapon_blocks = top_level_blocks(WEAPON_PATH.read_text(encoding="utf-8"))
    setup_blocks = top_level_blocks(SETUP_PATH.read_text(encoding="utf-8"))
    users = weapon_users(weapon_blocks)
    entries = {}; unresolved = []; class_counts = Counter()

    for unique_name, unique in registry.get("uniques", {}).items():
        class_name = unique["class"]; base_name = unique["base_family"]; class_counts[class_name] += 1
        base = base_families.get((class_name, base_name))
        if not base:
            unresolved.append({"unique": unique_name, "reason": "base_family_not_found", "class": class_name, "base_family": base_name}); continue

        unique_setup = unique["general_setup_sid"]; base_setup = base.get("general_setup_sid"); base_weapon = base.get("weapon_sid")
        unique_weapon = choose_unique_weapon(unique_setup, users)
        unique_setup_effective, unique_setup_chain = effective_properties(unique_setup, setup_blocks)
        base_setup_effective, base_setup_chain = effective_properties(base_setup, setup_blocks)
        setup_diff = top_level_diff(base_setup_effective, unique_setup_effective)
        setup_leaf = leaf_diff(base_setup_effective, unique_setup_effective)
        setup_direct = direct_properties(setup_blocks[unique_setup]) if unique_setup in setup_blocks else {}

        weapon_diff = {}; weapon_leaf: list[dict[str, object]] = []; weapon_direct = {}; unique_weapon_chain: list[str] = []; base_weapon_chain: list[str] = []
        if unique_weapon and base_weapon and unique_weapon in weapon_blocks and base_weapon in weapon_blocks:
            unique_weapon_effective, unique_weapon_chain = effective_properties(unique_weapon, weapon_blocks)
            base_weapon_effective, base_weapon_chain = effective_properties(base_weapon, weapon_blocks)
            weapon_diff = top_level_diff(base_weapon_effective, unique_weapon_effective)
            weapon_leaf = leaf_diff(base_weapon_effective, unique_weapon_effective)
            weapon_direct = direct_properties(weapon_blocks[unique_weapon])

        candidate_leaf = filtered_leaf_diffs(setup_leaf + weapon_leaf)
        candidate_fields = sorted({str(entry["path"]).split(".", 1)[0] for entry in candidate_leaf})
        entries[unique_name] = {
            "class": class_name, "base_family": base_name,
            "unique_general_setup_sid": unique_setup, "base_general_setup_sid": base_setup,
            "unique_weapon_sid": unique_weapon, "base_weapon_sid": base_weapon,
            "linked_weapon_candidates": users.get(unique_setup, []),
            "signature_candidate_fields": candidate_fields,
            "signature_candidate_leaf_diffs": candidate_leaf,
            "general_setup": {"inheritance_chain": unique_setup_chain, "base_inheritance_chain": base_setup_chain, "direct_overrides": setup_direct, "effective_diff_vs_base": setup_diff, "leaf_diff_vs_base": setup_leaf},
            "weapon_prototype": {"inheritance_chain": unique_weapon_chain, "base_inheritance_chain": base_weapon_chain, "direct_overrides": weapon_direct, "effective_diff_vs_base": weapon_diff, "leaf_diff_vs_base": weapon_leaf},
        }

    return {
        "summary": {"registry_uniques": len(registry.get("uniques", {})), "analyzed": len(entries), "unresolved": len(unresolved), "by_class": dict(sorted(class_counts.items()))},
        "notes": [
            "effective values resolve refkey inheritance before comparison.",
            "Nested structs are parsed structurally and deep-merged so inherited leaves are retained.",
            "leaf_diff_vs_base reports changed leaf paths instead of replacing an entire nested struct in the compact view.",
            "numeric_delta.percent is the relative Unique-vs-base change when both leaves are compatible numeric values and the base is non-zero.",
            "signature_candidate_leaf_diffs filters identity/plumbing fields but remains analysis evidence, not an automatic balance recommendation.",
        ],
        "unresolved": unresolved, "uniques": entries, "out_of_scope": registry.get("out_of_scope", {}),
    }


def format_leaf(entry: dict[str, object]) -> str:
    base = entry.get("base"); unique = entry.get("unique"); suffix = ""
    delta = entry.get("numeric_delta")
    if isinstance(delta, dict):
        parts = []
        if "absolute" in delta: parts.append(f"Δ {delta['absolute']:+g}")
        if "percent" in delta: parts.append(f"{delta['percent']:+.1f}%")
        if parts: suffix = " (" + ", ".join(parts) + ")"
    return f"    {entry['path']}: {base} -> {unique}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Vanilla Unique weapons with their BPRUE base families.")
    parser.add_argument("--output", type=Path, default=UNIQUE_WEAPON_ANALYSIS)
    parser.add_argument("--print-details", action="store_true", help="Print leaf-level Unique-vs-base differences after the summary.")
    args = parser.parse_args()
    report = analyze(); ensure_reports_dir()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(f"Unique weapon analysis: registry={summary['registry_uniques']} | analyzed={summary['analyzed']} | unresolved={summary['unresolved']}")
    print("By class: " + ", ".join(f"{key}={value}" for key, value in summary["by_class"].items()))
    print(f"Report: {args.output}")
    if args.print_details:
        for name, entry in report["uniques"].items():
            print(f"\n{name} [{entry['class']}] <- {entry['base_family']}")
            diffs = entry["signature_candidate_leaf_diffs"]
            if not diffs: print("    (no non-plumbing differences)")
            else:
                for diff in diffs: print(format_leaf(diff))
    if report["unresolved"]:
        print("Unresolved:")
        for entry in report["unresolved"]: print(f"  - {entry['unique']}: {entry['reason']}")


if __name__ == "__main__":
    main()
