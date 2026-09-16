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
VANILLA_ROOT = PYTHON_ROOT / "VanillaReference"
VANILLA_WEAPONS = VANILLA_ROOT / "WeaponPrototypes.cfg"
VANILLA_GENERAL_SETUPS = VANILLA_ROOT / "WeaponGeneralSetupPrototypes.cfg"
VANILLA_UPGRADES = VANILLA_ROOT / "UpgradePrototypes.cfg"
DLC_ROOT = VANILLA_ROOT / "DLCGameData"
UNIQUE_REGISTRY = CFG_ROOT / "Common" / "unique_weapons.json"
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


def direct_array_values(block: list[str], name: str) -> list[str]:
    values = []; in_array = False; depth = 0
    start = re.compile(rf"\s*{re.escape(name)}\s*:\s*struct\.begin")
    value = re.compile(r"\s*\[\d+\]\s*=\s*(.+?)\s*$")
    for line in block[1:-1]:
        stripped = line.strip()
        if not in_array:
            if start.match(line): in_array = True; depth = 1
            continue
        if "struct.begin" in stripped: depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0: break
            continue
        if depth == 1:
            match = value.match(line)
            if match: values.append(match.group(1).strip())
    return values


def refkey(block: list[str] | None) -> str | None:
    if not block: return None
    match = re.search(r"(?:\{|;)refkey=([^;}]+)", block[0])
    return match.group(1).strip() if match else None


def refurl(block: list[str] | None) -> str | None:
    if not block: return None
    match = re.search(r"(?:\{|;)refurl=([^;}]+)", block[0])
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


def load_unique_registry() -> tuple[dict[str, dict], dict[str, dict]]:
    if not UNIQUE_REGISTRY.exists(): return {}, {}
    config = json.loads(UNIQUE_REGISTRY.read_text(encoding="utf-8"))
    uniques = {}
    for name, entry in config.get("uniques", {}).items():
        setup_sid = entry.get("general_setup_sid")
        if setup_sid: uniques[setup_sid] = {"name": name, **entry, "source": str(UNIQUE_REGISTRY.relative_to(PYTHON_ROOT))}
    out_of_scope = {}
    for name, entry in config.get("out_of_scope", {}).items():
        setup_sid = entry.get("general_setup_sid")
        if setup_sid: out_of_scope[setup_sid] = {"name": name, **entry, "source": str(UNIQUE_REGISTRY.relative_to(PYTHON_ROOT))}
    return uniques, out_of_scope


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
    result = {}
    for weapon_sid, block in weapon_blocks.items():
        if weapon_sid in bases: continue
        base_sid = inherited_base_weapon(weapon_sid, weapon_blocks, bases)
        if not base_sid: continue
        setup_sid = direct_scalar(block, "GeneralWeaponSetup")
        if not setup_sid: continue
        base = bases[base_sid]
        result[setup_sid] = {"weapon_sid": weapon_sid, "general_setup_sid": setup_sid, "class": base["class"],
                             "base_weapon_sid": base_sid, "base_family": base["family"],
                             "inheritance_chain": inheritance_chain(weapon_sid, weapon_blocks),
                             "discovery": "weapon_inherits_bprue_base_weapon"}
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
    reasons = []; lower_sid = setup_sid.lower()
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


def resolve_setup_base(sid: str, local_blocks: dict[str, list[str]], vanilla_blocks: dict[str, list[str]], configured: dict[str, dict]) -> dict | None:
    seen = {sid}; current = sid; chain = []
    while True:
        block = local_blocks.get(current) or vanilla_blocks.get(current)
        if not block: break
        parent = refkey(block)
        if not parent or parent in seen or parent.startswith("["): break
        chain.append(parent); seen.add(parent)
        if parent in configured:
            base = configured[parent]
            return {"general_setup_sid": parent, "family": base["family"], "class": base["class"], "inheritance_chain": chain}
        current = parent
    return None


def resolve_dlc_item_base(setup_sid: str, dlc_item_blocks: dict[str, list[str]], vanilla_weapon_blocks: dict[str, list[str]], bases: dict[str, dict]) -> dict | None:
    """Resolve a DLC GeneralSetup through the DLC ItemPrototype that uses it.

    DLC weapons may introduce a new GeneralSetup that does not inherit a vanilla
    GeneralSetup. Their ItemPrototype can still inherit a vanilla WeaponPrototype,
    which gives us the authoritative BPRUE family mapping.
    """
    combined_blocks = {**vanilla_weapon_blocks, **dlc_item_blocks}
    for weapon_sid, block in dlc_item_blocks.items():
        if direct_scalar(block, "GeneralWeaponSetup") != setup_sid:
            continue
        chain = inheritance_chain(weapon_sid, combined_blocks)
        base_weapon_sid = next((parent for parent in chain if parent in bases), None)
        if not base_weapon_sid:
            continue
        base = bases[base_weapon_sid]
        return {
            "weapon_sid": weapon_sid,
            "base_weapon_sid": base_weapon_sid,
            "family": base["family"],
            "class": base["class"],
            "inheritance_chain": chain,
        }
    return None


def discover_dlc(configured: dict[str, dict], vanilla_setup_blocks: dict[str, list[str]], vanilla_weapon_blocks: dict[str, list[str]]) -> dict:
    vanilla_upgrade_sids = set(top_level_blocks(VANILLA_UPGRADES.read_text(encoding="utf-8"))) if VANILLA_UPGRADES.exists() else set()
    bases = base_weapon_index(configured)
    packs = {}; all_entries = []
    setup_files = sorted(DLC_ROOT.glob("*/WeaponData/WeaponGeneralSetupPrototypes.cfg")) if DLC_ROOT.exists() else []
    for path in setup_files:
        pack = path.relative_to(DLC_ROOT).parts[0]
        blocks = top_level_blocks(path.read_text(encoding="utf-8"))
        item_path = DLC_ROOT / pack / "ItemPrototypes.cfg"
        item_blocks = top_level_blocks(item_path.read_text(encoding="utf-8")) if item_path.exists() else {}
        entries = []
        for sid, block in sorted(blocks.items()):
            if not sid.startswith("Gun"): continue
            setup_base = resolve_setup_base(sid, blocks, vanilla_setup_blocks, configured)
            item_base = None if setup_base else resolve_dlc_item_base(sid, item_blocks, vanilla_weapon_blocks, bases)
            upgrade_sids = direct_array_values(block, "UpgradePrototypeSIDs")
            unknown_upgrades = sorted(set(upgrade_sids) - vanilla_upgrade_sids)
            if setup_base:
                weapon_class = setup_base["class"]; base_family = setup_base["family"]
                base_setup_sid = setup_base["general_setup_sid"]; base_weapon_sid = None
                setup_chain = setup_base["inheritance_chain"]; weapon_sid = None; weapon_chain = []
                resolution = "general_setup_inheritance"
            elif item_base:
                weapon_class = item_base["class"]; base_family = item_base["family"]
                base_setup_sid = configured.get(next((key for key, value in configured.items() if value["family"] == base_family and value["class"] == weapon_class), ""), {}).get("general_setup_sid")
                base_weapon_sid = item_base["base_weapon_sid"]
                setup_chain = inheritance_chain(sid, {**vanilla_setup_blocks, **blocks})
                weapon_sid = item_base["weapon_sid"]; weapon_chain = item_base["inheritance_chain"]
                resolution = "item_prototype_inheritance"
            else:
                weapon_class = class_from_sid(sid); base_family = None; base_setup_sid = None; base_weapon_sid = None
                setup_chain = inheritance_chain(sid, {**vanilla_setup_blocks, **blocks})
                weapon_sid = None; weapon_chain = []; resolution = None
            entry = {
                "content_pack": pack,
                "output_scope": f"DLCGameData/{pack}",
                "general_setup_sid": sid,
                "weapon_sid": weapon_sid,
                "refkey": refkey(block),
                "refurl": refurl(block),
                "class": weapon_class,
                "base_family": base_family,
                "base_general_setup_sid": base_setup_sid,
                "base_weapon_sid": base_weapon_sid,
                "inheritance_chain": setup_chain,
                "weapon_inheritance_chain": weapon_chain,
                "resolution": resolution,
                "upgrade_prototype_count": len(upgrade_sids),
                "unknown_upgrade_prototype_sids": unknown_upgrades,
                "status": "resolved_base" if base_family else "unknown_base",
                "source": str(path.relative_to(PYTHON_ROOT)),
                "item_source": str(item_path.relative_to(PYTHON_ROOT)) if item_path.exists() else None,
            }
            entries.append(entry); all_entries.append(entry)
        packs[pack] = {
            "source": str(path.relative_to(PYTHON_ROOT)),
            "item_source": str(item_path.relative_to(PYTHON_ROOT)) if item_path.exists() else None,
            "output_scope": f"DLCGameData/{pack}",
            "candidate_general_setups": len(entries),
            "resolved_bases": sum(e["status"] == "resolved_base" for e in entries),
            "resolved_via_items": sum(e["resolution"] == "item_prototype_inheritance" for e in entries),
            "unknown_bases": sum(e["status"] == "unknown_base" for e in entries),
            "setups_with_unknown_upgrades": sum(bool(e["unknown_upgrade_prototype_sids"]) for e in entries),
            "weapons": entries,
        }
    return {
        "summary": {
            "content_packs": len(packs),
            "candidate_general_setups": len(all_entries),
            "resolved_bases": sum(e["status"] == "resolved_base" for e in all_entries),
            "resolved_via_items": sum(e["resolution"] == "item_prototype_inheritance" for e in all_entries),
            "unknown_bases": sum(e["status"] == "unknown_base" for e in all_entries),
            "setups_with_unknown_upgrades": sum(bool(e["unknown_upgrade_prototype_sids"]) for e in all_entries),
            "unknown_upgrade_references": sum(len(e["unknown_upgrade_prototype_sids"]) for e in all_entries),
        },
        "packs": packs,
    }


def build_report() -> dict:
    weapon_blocks = top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8"))
    setup_blocks = top_level_blocks(VANILLA_GENERAL_SETUPS.read_text(encoding="utf-8"))
    configured = configured_weapons(); unique_covered, out_of_scope = load_unique_registry()
    setup_users = weapons_by_general_setup(weapon_blocks); bases = base_weapon_index(configured)
    variants = discovered_variant_setups(weapon_blocks, bases)
    base_covered_setups = set(configured); unique_covered_setups = set(unique_covered); out_of_scope_setups = set(out_of_scope)
    vanilla_setups = ({sid for sid in setup_blocks if sid.startswith("Gun") and class_from_sid(sid) is not None} | set(variants) | out_of_scope_setups)
    buckets = {"suspected_missing_base_weapons": [], "suspected_unique_or_special": [], "needs_manual_review": []}
    covered_unique_entries = []; out_of_scope_entries = []

    for setup_sid in sorted(vanilla_setups):
        if setup_sid in out_of_scope_setups:
            registry = out_of_scope[setup_sid]; variant = variants.get(setup_sid)
            out_of_scope_entries.append({"general_setup_sid": setup_sid,
                                         "class": variant["class"] if variant else class_from_sid(setup_sid),
                                         "name": registry["name"], "reason": registry.get("reason", "out_of_scope")})
            continue
        if setup_sid in unique_covered_setups:
            registry = unique_covered[setup_sid]; variant = variants.get(setup_sid)
            covered_unique_entries.append({"general_setup_sid": setup_sid, "name": registry["name"],
                                           "class": registry.get("class") or (variant["class"] if variant else class_from_sid(setup_sid)),
                                           "base_family": registry.get("base_family"),
                                           "base_weapon_sid": variant.get("base_weapon_sid") if variant else None,
                                           "status": "covered_unique"})
            continue
        if setup_sid in base_covered_setups: continue
        evidence = candidate_evidence(setup_sid, weapon_blocks, setup_blocks, setup_users); variant = variants.get(setup_sid)
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
    unique_counts = Counter(x["class"] or "Unknown" for x in covered_unique_entries)
    dlc = discover_dlc(configured, setup_blocks, weapon_blocks)
    return {
        "sources": {"weapon_prototypes": str(VANILLA_WEAPONS.relative_to(PYTHON_ROOT)),
                    "general_setups": str(VANILLA_GENERAL_SETUPS.relative_to(PYTHON_ROOT)),
                    "upgrade_prototypes": str(VANILLA_UPGRADES.relative_to(PYTHON_ROOT)),
                    "dlc_root": str(DLC_ROOT.relative_to(PYTHON_ROOT)),
                    "bprue_configs": [str(p.relative_to(PYTHON_ROOT)) for p in CONFIGS if p.exists()],
                    "unique_registry": str(UNIQUE_REGISTRY.relative_to(PYTHON_ROOT))},
        "rules": {
            "candidate_scope": "Supported-class base-game GeneralSetups plus inherited variants and explicit out-of-scope entries; DLC GeneralSetups are audited separately.",
            "variant_discovery": "WeaponPrototype inheritance is authoritative for assigning unusual base-game Unique GeneralSetup names to a BPRUE base family/class.",
            "dlc_discovery": "DLC GeneralSetup inheritance is resolved first. If it does not reach a configured BPRUE family, the matching DLC ItemPrototype is resolved through its WeaponPrototype inheritance chain.",
            "dlc_output_scope": "DLC discoveries retain their DLCGameData/<pack> output scope so future generated patches are not mixed into base-game GameData output.",
            "dlc_upgrade_audit": "DLC UpgradePrototypeSIDs are checked against base-game UpgradePrototypes.cfg; unknown references are reported for follow-up.",
            "base_covered": "GeneralSetup SID is present in a BPRUE base-family generator config.",
            "unique_covered": "GeneralSetup SID is present in Common/unique_weapons.json under uniques.",
            "out_of_scope": "GeneralSetup SID is explicitly excluded in Common/unique_weapons.json under out_of_scope."},
        "summary": {"vanilla_candidate_general_setups": len(vanilla_setups),
                    "inheritance_discovered_variant_setups": len(variants),
                    "bprue_base_general_setups": len(base_covered_setups),
                    "bprue_unique_general_setups": len(covered_unique_entries),
                    "bprue_total_covered_general_setups": len((base_covered_setups | {x['general_setup_sid'] for x in covered_unique_entries}) & vanilla_setups),
                    "out_of_scope": len(out_of_scope_entries),
                    "suspected_missing_base_weapons": len(buckets["suspected_missing_base_weapons"]),
                    "suspected_unique_or_special": len(buckets["suspected_unique_or_special"]),
                    "needs_manual_review": len(buckets["needs_manual_review"]),
                    "covered_uniques_by_class": dict(sorted(unique_counts.items())),
                    "suspected_missing_by_class": dict(sorted(missing_counts.items())),
                    "suspected_unique_or_special_by_class": dict(sorted(variant_counts.items())),
                    "manual_review_by_class": dict(sorted(review_counts.items()))},
        "bprue_base_covered": [configured[sid] for sid in sorted(configured)],
        "bprue_unique_covered": covered_unique_entries,
        "out_of_scope": out_of_scope_entries,
        "dlc": dlc,
        **buckets}


def print_entries(title, entries, show_reasons=False):
    print(f"\n{title}:")
    if not entries: print("  <none>"); return
    for entry in entries:
        suffix = " <- " + ", ".join(entry["reasons"]) if show_reasons and entry.get("reasons") else ""
        print(f"  [{entry.get('class') or 'Unknown':<13}] {entry['general_setup_sid']}{suffix}")


def print_dlc_report(dlc: dict, show_variants: bool):
    s = dlc["summary"]
    print(f"\nDLC candidates={s['candidate_general_setups']} | packs={s['content_packs']} | resolved bases={s['resolved_bases']} | via items={s['resolved_via_items']} | unknown bases={s['unknown_bases']} | setups with unknown upgrades={s['setups_with_unknown_upgrades']} | unknown upgrade refs={s['unknown_upgrade_references']}")
    for pack, data in dlc["packs"].items():
        print(f"  {pack:<10} candidates={data['candidate_general_setups']} | resolved={data['resolved_bases']} | via items={data['resolved_via_items']} | unknown bases={data['unknown_bases']} | unknown upgrades={data['setups_with_unknown_upgrades']}")
    unknown_bases = [e for p in dlc["packs"].values() for e in p["weapons"] if e["status"] == "unknown_base"]
    unknown_upgrades = [e for p in dlc["packs"].values() for e in p["weapons"] if e["unknown_upgrade_prototype_sids"]]
    print_entries("DLC GeneralSetups with unknown base", unknown_bases)
    if unknown_upgrades:
        print("\nDLC GeneralSetups with unknown UpgradePrototypeSIDs:")
        for entry in unknown_upgrades:
            print(f"  [{entry['content_pack']:<10}] {entry['general_setup_sid']} <- {', '.join(entry['unknown_upgrade_prototype_sids'])}")
    else:
        print("\nDLC GeneralSetups with unknown UpgradePrototypeSIDs:\n  <none>")
    if show_variants:
        print("\nResolved DLC variants:")
        for pack in dlc["packs"].values():
            for entry in pack["weapons"]:
                if entry["status"] != "resolved_base": continue
                if entry["resolution"] == "item_prototype_inheritance":
                    print(f"  [{entry['content_pack']:<10}] {entry['general_setup_sid']} -> {entry['weapon_sid']} -> {entry['base_weapon_sid']} -> {entry['base_family']} [item inheritance]")
                else:
                    print(f"  [{entry['content_pack']:<10}] {entry['general_setup_sid']} -> {entry['base_general_setup_sid']} -> {entry['base_family']}")


def print_report(report, show_variants=False):
    s = report["summary"]
    print(f"Vanilla candidates={s['vanilla_candidate_general_setups']} | inherited variants={s['inheritance_discovered_variant_setups']} | BPRUE base={s['bprue_base_general_setups']} | BPRUE uniques={s['bprue_unique_general_setups']} | out of scope={s['out_of_scope']} | missing base?={s['suspected_missing_base_weapons']} | uncovered variants?={s['suspected_unique_or_special']} | manual review={s['needs_manual_review']}")
    print_entries("Suspected missing base weapons", report["suspected_missing_base_weapons"])
    print_entries("Needs manual review", report["needs_manual_review"], True)
    if show_variants:
        print_entries("BPRUE-covered Unique variants", report["bprue_unique_covered"])
        print_entries("Out of scope", report["out_of_scope"])
        print_entries("Uncovered unique/special variants", report["suspected_unique_or_special"], True)
    print_dlc_report(report["dlc"], show_variants)


def main():
    parser = argparse.ArgumentParser(description="Compare base-game and DLC weapon coverage with BPRUE, including the central Unique registry and explicit out-of-scope weapons.")
    parser.add_argument("--show-variants", "--show-excluded", dest="show_variants", action="store_true",
                        help="Also print covered Uniques, out-of-scope weapons, uncovered variants and resolved DLC mappings")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="JSON report path")
    args = parser.parse_args(); report = build_report(); args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8"); print_report(report, args.show_variants); print(f"\nWrote {args.output}")


if __name__ == "__main__": main()
