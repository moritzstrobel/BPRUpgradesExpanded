from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from analysis_paths import WEAPON_COVERAGE

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
CFG_ROOT = PYTHON_ROOT / "CFGGenerators"
VANILLA_WEAPONS = PYTHON_ROOT / "VanillaReference" / "WeaponPrototypes.cfg"
VANILLA_GENERAL_SETUPS = PYTHON_ROOT / "VanillaReference" / "WeaponGeneralSetupPrototypes.cfg"
OUTPUT_PATH = WEAPON_COVERAGE

CONFIGS = (
    CFG_ROOT / "AssaultRifles" / "assault_rifles_upgrades.json",
    CFG_ROOT / "SMGs" / "smg_upgrades.json",
    CFG_ROOT / "Shotguns" / "shotgun_upgrades.json",
    CFG_ROOT / "Pistols" / "pistol_upgrades.json",
    CFG_ROOT / "Snipers" / "sniper_upgrades.json",
    CFG_ROOT / "MachineGuns" / "machine_gun_upgrades.json",
)

UNIQUE_NAME_MARKERS = ("unique", "quest", "special", "prototype", "test", "debug")
WEAPON_CLASS_SUFFIXES = {
    "ST": "AssaultRifles", "PP": "SMGs", "HG": "Pistols", "SG": "Shotguns",
    "SP": "Snipers", "DMR": "Snipers", "MG": "MachineGuns",
}


def top_level_blocks(text: str) -> dict[str, list[str]]:
    blocks: dict[str, list[str]] = {}; current = None; depth = 0; sid = ""
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


def direct_scalar(block: list[str], name: str) -> str | None:
    pattern = re.compile(rf"\s*{re.escape(name)}\s*=\s*(.+?)\s*$"); depth = 0
    for line in block[1:-1]:
        stripped = line.strip()
        if "struct.begin" in stripped: depth += 1; continue
        if stripped == "struct.end": depth -= 1; continue
        if depth: continue
        match = pattern.match(line)
        if match: return match.group(1).strip()
    return None


def refkey(block: list[str] | None) -> str | None:
    if not block: return None
    match = re.search(r"\{refkey=([^}]+)\}", block[0])
    return match.group(1).strip() if match else None


def inheritance_chain(sid: str, blocks: dict[str, list[str]]) -> list[str]:
    chain = []; seen = {sid}; current = sid
    while current in blocks:
        parent = refkey(blocks[current])
        if not parent or parent in seen or parent.startswith("["): break
        chain.append(parent); seen.add(parent); current = parent
    return chain


def concrete_gun_parent(chain: list[str]) -> str | None:
    return next((parent for parent in chain if parent.startswith("Gun")), None)


def configured_weapons() -> dict[str, dict]:
    result = {}
    for path in CONFIGS:
        if not path.exists(): continue
        config = json.loads(path.read_text(encoding="utf-8")); weapon_class = path.parent.name
        for family_name, family in config.get("families", {}).items():
            weapon_sid = family.get("weapon_sid"); setup_sid = family.get("general_setup_sid")
            if not weapon_sid and not setup_sid: continue
            key = setup_sid or weapon_sid
            result[key] = {"family": family_name, "class": weapon_class, "weapon_sid": weapon_sid,
                           "general_setup_sid": setup_sid, "source": str(path.relative_to(PYTHON_ROOT))}
        if weapon_class == "SMGs":
            for family_name, family in config.get("caliber_families", {}).items():
                setup_sid = family.get("general_setup_sid")
                if setup_sid and setup_sid not in result:
                    result[setup_sid] = {"family": family_name, "class": weapon_class, "weapon_sid": None,
                                         "general_setup_sid": setup_sid, "source": str(path.relative_to(PYTHON_ROOT)),
                                         "caliber_only": True}
    return result


def class_from_sid(sid: str) -> str | None:
    for part in reversed(sid.split("_")):
        if part in WEAPON_CLASS_SUFFIXES: return WEAPON_CLASS_SUFFIXES[part]
    return None


def weapons_by_general_setup(weapon_blocks: dict[str, list[str]]) -> dict[str, list[str]]:
    result = defaultdict(list)
    for weapon_sid, block in weapon_blocks.items():
        setup_sid = direct_scalar(block, "GeneralWeaponSetup")
        if setup_sid: result[setup_sid].append(weapon_sid)
    return {setup: sorted(sids) for setup, sids in result.items()}


def base_weapon_index(configured: dict[str, dict]) -> dict[str, dict]:
    return {entry["weapon_sid"]: entry for entry in configured.values() if entry.get("weapon_sid")}


def inherited_base_weapon(weapon_sid: str, weapon_blocks: dict[str, list[str]], bases: dict[str, dict]) -> str | None:
    return next((parent for parent in inheritance_chain(weapon_sid, weapon_blocks) if parent in bases), None)


def discovered_variant_setups(weapon_blocks: dict[str, list[str]], bases: dict[str, dict]) -> dict[str, dict]:
    """Find variants from WeaponPrototype inheritance, independent of GeneralSetup naming."""
    result = {}
    for weapon_sid, block in weapon_blocks.items():
        if weapon_sid in bases: continue
        base_sid = inherited_base_weapon(weapon_sid, weapon_blocks, bases)
        if not base_sid: continue
        setup_sid = direct_scalar(block, "GeneralWeaponSetup")
        if not setup_sid: continue
        base = bases[base_sid]
        result[setup_sid] = {
            "weapon_sid": weapon_sid,
            "general_setup_sid": setup_sid,
            "class": base["class"],
            "base_weapon_sid": base_sid,
            "base_family": base["family"],
            "inheritance_chain": inheritance_chain(weapon_sid, weapon_blocks),
            "discovery": "weapon_inherits_bprue_base_weapon",
        }
    return result


def candidate_evidence(setup_sid, weapon_blocks, setup_blocks, setup_users) -> dict:
    same_weapon = weapon_blocks.get(setup_sid); linked_weapons = setup_users.get(setup_sid, [])
    setup_chain = inheritance_chain(setup_sid, setup_blocks); same_chain = inheritance_chain(setup_sid, weapon_blocks) if same_weapon else []
    linked = []
    for weapon_sid in linked_weapons:
        chain = inheritance_chain(weapon_sid, weapon_blocks)
        linked.append({"weapon_sid": weapon_sid, "inheritance_chain": chain,
                       "concrete_gun_parent": concrete_gun_parent(chain),
                       "localization_sid": direct_scalar(weapon_blocks[weapon_sid], "LocalizationSID")})
    return {"same_sid_weapon_prototype": same_weapon is not None,
            "same_sid_weapon_inheritance_chain": same_chain,
            "same_sid_weapon_concrete_gun_parent": concrete_gun_parent(same_chain),
            "general_setup_inheritance_chain": setup_chain,
            "general_setup_concrete_gun_parent": concrete_gun_parent(setup_chain),
            "linked_weapon_prototypes": linked}


def classify_candidate(setup_sid: str, evidence: dict) -> tuple[str, list[str]]:
    reasons = []
    lower_sid = setup_sid.lower()
    for marker in UNIQUE_NAME_MARKERS:
        if marker in lower_sid: reasons.append(f"sid_marker:{marker}")
    if evidence["same_sid_weapon_concrete_gun_parent"]:
        reasons.append(f"weapon_inherits_concrete_weapon:{evidence['same_sid_weapon_concrete_gun_parent']}")
    if evidence["general_setup_concrete_gun_parent"]:
        reasons.append(f"setup_inherits_concrete_setup:{evidence['general_setup_concrete_gun_parent']}")
    for linked in evidence["linked_weapon_prototypes"]:
        if linked["concrete_gun_parent"]: reasons.append(f"linked_weapon:{linked['weapon_sid']}:inherits:{linked['concrete_gun_parent']}")
    if reasons: return "suspected_unique_or_special", reasons
    if evidence["same_sid_weapon_prototype"]: return "suspected_missing_base_weapon", ["standalone_weapon_and_setup_not_covered_by_bprue"]
    if evidence["linked_weapon_prototypes"]: return "needs_manual_review", ["setup_has_linked_weapon_but_no_structural_variant_signal"]
    return "needs_manual_review", ["no_same_sid_or_linked_weapon_prototype"]


def build_report() -> dict:
    weapon_blocks = top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8"))
    setup_blocks = top_level_blocks(VANILLA_GENERAL_SETUPS.read_text(encoding="utf-8"))
    configured = configured_weapons(); setup_users = weapons_by_general_setup(weapon_blocks)
    bases = base_weapon_index(configured); variants = discovered_variant_setups(weapon_blocks, bases)
    covered_setups = set(configured); covered_weapon_sids = set(bases)

    # Keep the old GeneralSetup-based discovery for standalone bases/specials, but
    # union it with inheritance-discovered variants so unusual SIDs such as
    # Gun_Drowned_AR_GS and Gun_Trophy_AR_GS cannot fall out of candidate scope.
    vanilla_setups = {sid for sid in setup_blocks if sid.startswith("Gun") and class_from_sid(sid) is not None} | set(variants)
    buckets = {"suspected_missing_base_weapons": [], "suspected_unique_or_special": [], "needs_manual_review": []}

    for setup_sid in sorted(vanilla_setups):
        if setup_sid in covered_setups: continue
        evidence = candidate_evidence(setup_sid, weapon_blocks, setup_blocks, setup_users)
        variant = variants.get(setup_sid)
        if variant:
            status = "suspected_unique_or_special"
            reasons = [f"weapon_inherits_bprue_base:{variant['base_weapon_sid']}", f"base_family:{variant['base_family']}"]
        else:
            status, reasons = classify_candidate(setup_sid, evidence)
        weapon_class = variant["class"] if variant else class_from_sid(setup_sid)
        entry = {"general_setup_sid": setup_sid, "class": weapon_class, "status": status,
                 "reasons": reasons, "evidence": evidence}
        if variant: entry["variant_mapping"] = variant
        key = "suspected_missing_base_weapons" if status == "suspected_missing_base_weapon" else status
        buckets[key].append(entry)

    missing_counts = Counter(x["class"] or "Unknown" for x in buckets["suspected_missing_base_weapons"])
    variant_counts = Counter(x["class"] or "Unknown" for x in buckets["suspected_unique_or_special"])
    review_counts = Counter(x["class"] or "Unknown" for x in buckets["needs_manual_review"])
    return {
        "sources": {"weapon_prototypes": str(VANILLA_WEAPONS.relative_to(PYTHON_ROOT)),
                    "general_setups": str(VANILLA_GENERAL_SETUPS.relative_to(PYTHON_ROOT)),
                    "bprue_configs": [str(p.relative_to(PYTHON_ROOT)) for p in CONFIGS if p.exists()]},
        "rules": {
            "candidate_scope": "Supported-class GeneralSetups plus every WeaponPrototype whose inheritance chain reaches a configured BPRUE base weapon.",
            "variant_discovery": "WeaponPrototype inheritance is authoritative for assigning unusual Unique GeneralSetup names to a BPRUE base family/class.",
            "covered": "GeneralSetup SID is present in a BPRUE generator config.",
            "suspected_missing_base_weapon": "Uncovered standalone supported-class setup without concrete Gun* inheritance evidence.",
            "suspected_unique_or_special": "Uncovered setup with variant inheritance evidence, including inheritance from a configured BPRUE base weapon.",
            "needs_manual_review": "Uncovered setup that cannot be classified confidently from Vanilla structure alone.",
            "important": "Class/base-family assignment for inherited variants is structural; the Unique/special label remains a candidate classification."
        },
        "summary": {"vanilla_candidate_general_setups": len(vanilla_setups),
                    "inheritance_discovered_variant_setups": len(variants),
                    "bprue_configured_general_setups": len(covered_setups),
                    "bprue_configured_weapon_sids": len(covered_weapon_sids),
                    "suspected_missing_base_weapons": len(buckets["suspected_missing_base_weapons"]),
                    "suspected_unique_or_special": len(buckets["suspected_unique_or_special"]),
                    "needs_manual_review": len(buckets["needs_manual_review"]),
                    "suspected_missing_by_class": dict(sorted(missing_counts.items())),
                    "suspected_unique_or_special_by_class": dict(sorted(variant_counts.items())),
                    "manual_review_by_class": dict(sorted(review_counts.items()))},
        "bprue_covered": [configured[sid] for sid in sorted(configured)], **buckets}


def print_entries(title, entries, show_reasons=False):
    print(f"\n{title}:")
    if not entries: print("  <none>"); return
    for entry in entries:
        suffix = " <- " + ", ".join(entry["reasons"]) if show_reasons else ""
        print(f"  [{entry['class'] or 'Unknown':<13}] {entry['general_setup_sid']}{suffix}")


def print_report(report, show_variants=False):
    s = report["summary"]
    print(f"Vanilla candidates={s['vanilla_candidate_general_setups']} | inherited variants={s['inheritance_discovered_variant_setups']} | BPRUE setups={s['bprue_configured_general_setups']} | missing base?={s['suspected_missing_base_weapons']} | unique/special?={s['suspected_unique_or_special']} | manual review={s['needs_manual_review']}")
    print_entries("Suspected missing base weapons", report["suspected_missing_base_weapons"])
    print_entries("Needs manual review", report["needs_manual_review"], True)
    if show_variants: print_entries("Suspected unique/special variants", report["suspected_unique_or_special"], True)


def main():
    parser = argparse.ArgumentParser(description="Compare Vanilla weapon coverage with BPRUE and discover variants through WeaponPrototype inheritance.")
    parser.add_argument("--show-variants", "--show-excluded", dest="show_variants", action="store_true",
                        help="Also print suspected unique/special variants and their base-family evidence")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON report path")
    args = parser.parse_args(); report = build_report(); args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8"); print_report(report, args.show_variants); print(f"\nWrote {args.output}")


if __name__ == "__main__": main()
