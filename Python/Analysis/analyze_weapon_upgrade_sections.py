from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from analysis_paths import WEAPON_UPGRADE_SECTIONS, ensure_reports_dir

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
CFG_ROOT = PYTHON_ROOT / "CFGGenerators"
VANILLA_WEAPONS = PYTHON_ROOT / "VanillaReference" / "WeaponPrototypes.cfg"
OUTPUT_PATH = WEAPON_UPGRADE_SECTIONS

CONFIGS = (
    CFG_ROOT / "AssaultRifles" / "assault_rifles_upgrades.json", CFG_ROOT / "SMGs" / "smg_upgrades.json",
    CFG_ROOT / "Shotguns" / "shotgun_upgrades.json", CFG_ROOT / "Pistols" / "pistol_upgrades.json",
    CFG_ROOT / "Snipers" / "sniper_upgrades.json", CFG_ROOT / "MachineGuns" / "machine_gun_upgrades.json",
)


def top_level_blocks(text: str) -> dict[str, list[str]]:
    blocks = {}; current = None; depth = 0; sid = ""
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
            if depth == 0: blocks[sid] = current; current = None
    return blocks


def child_struct(block: list[str], name: str) -> list[str] | None:
    for index, line in enumerate(block):
        if line.strip().startswith(name + " : struct.begin"):
            child = [line]; depth = 1
            for nested in block[index + 1:]:
                child.append(nested); stripped = nested.strip()
                if "struct.begin" in stripped: depth += 1
                if stripped == "struct.end":
                    depth -= 1
                    if depth == 0: return child
    return None


def indexed_structs(block: list[str]) -> list[list[str]]:
    result = []; index = 1
    while index < len(block) - 1:
        if re.match(r"\s*\[\d+\]\s*:\s*struct\.begin", block[index]):
            item = [block[index]]; depth = 1; index += 1
            while index < len(block) and depth:
                item.append(block[index]); stripped = block[index].strip()
                if "struct.begin" in stripped: depth += 1
                if stripped == "struct.end": depth -= 1
                index += 1
            result.append(item); continue
        index += 1
    return result


def scalar(block: list[str], name: str) -> str | None:
    pattern = re.compile(rf"\s*{re.escape(name)}\s*=\s*(.+?)\s*$")
    for line in block:
        match = pattern.match(line)
        if match: return match.group(1)
    return None


def configured_weapons() -> dict[str, set[str]]:
    result = {}
    for path in CONFIGS:
        if not path.exists(): continue
        config = json.loads(path.read_text(encoding="utf-8")); weapon_class = path.parent.name
        for family in config.get("families", {}).values():
            weapon_sid = family.get("weapon_sid")
            if weapon_sid: result.setdefault(weapon_sid, set()).add(weapon_class)
        if weapon_class == "SMGs":
            for family in config.get("caliber_families", {}).values():
                setup_sid = family.get("general_setup_sid")
                if setup_sid == "GunM10_HG": result.setdefault("GunM10_HG", set()).add("SMGs")
    return result


def analyze_weapon(weapon_sid: str, block: list[str]) -> dict:
    sections_block = child_struct(block, "SectionSettings"); sections = []
    if sections_block:
        for item in indexed_structs(sections_block):
            target_raw = scalar(item, "UpgradeTargetPartType"); enabled_raw = scalar(item, "SectionIsEnabled")
            index_match = re.match(r"\s*\[(\d+)\]", item[0])
            sections.append({"index": int(index_match.group(1)) if index_match else None,
                             "target_part": target_raw.rsplit("::", 1)[-1] if target_raw else None,
                             "enabled": enabled_raw.lower() == "true" if enabled_raw else None,
                             "bottom": scalar(item, "BottomPosition"), "top": scalar(item, "TopPosition"),
                             "right": scalar(item, "RightPoition") or scalar(item, "RightPosition"),
                             "left": scalar(item, "LeftPosition"), "module_line_direction": scalar(item, "ModuleLineDirection"),
                             "upgrade_line_direction": scalar(item, "UpgradeLineDirection")})
    return {"weapon_sid": weapon_sid, "section_count": len(sections),
            "enabled_count": sum(s["enabled"] is True for s in sections),
            "disabled_count": sum(s["enabled"] is False for s in sections), "sections": sections}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Vanilla SectionSettings for BPRUE weapons")
    parser.add_argument("--all-vanilla", action="store_true", help="Analyze every Vanilla weapon block containing SectionSettings")
    args = parser.parse_args()
    if not VANILLA_WEAPONS.exists(): raise FileNotFoundError(VANILLA_WEAPONS)
    blocks = top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8")); configured = configured_weapons()
    weapon_sids = sorted(sid for sid, block in blocks.items() if child_struct(block, "SectionSettings")) if args.all_vanilla else sorted(configured)
    results = []; missing = []
    for weapon_sid in weapon_sids:
        block = blocks.get(weapon_sid)
        if not block: missing.append(weapon_sid); continue
        entry = analyze_weapon(weapon_sid, block); entry["classes"] = sorted(configured.get(weapon_sid, [])); results.append(entry)
    payload = {"weapon_count": len(results), "missing_weapons": missing, "section_count_distribution": {}, "weapons": results}
    for entry in results:
        count = str(entry["section_count"]); payload["section_count_distribution"][count] = payload["section_count_distribution"].get(count, 0) + 1
    ensure_reports_dir(); OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Analyzed {len(results)} weapons ({len(missing)} missing from Vanilla reference)")
    print("Section-count distribution:", payload["section_count_distribution"])
    for entry in results:
        section_text = ", ".join(f"{s['target_part']}={'ON' if s['enabled'] else 'off'}" for s in entry["sections"]) or "NO SectionSettings"
        print(f"{entry['weapon_sid']}: {entry['section_count']} sections | {section_text}")
    if missing: print("Missing:", ", ".join(missing))
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
