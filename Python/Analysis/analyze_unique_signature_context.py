from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from analyze_unique_weapons import (
    CLASS_CONFIGS,
    EQUIPMENT_FIELDS if False else GAMEPLAY_FIELDS,
    VANILLA_ROOT,
    direct_properties,
    effective_properties,
    leaf_diff,
    top_field,
    top_level_blocks,
)
from analysis_paths import ensure_reports_dir

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "Reports" / "unique_signature_context.json"
CFG_ROOT = Path(__file__).resolve().parent.parent / "CFGGenerators"
DLC_REGISTRY = CFG_ROOT / "Common" / "dlc_weapons.json"
DLC_ROOT = VANILLA_ROOT / "DLCGameData"
EQUIPMENT_FIELDS = {
    "CompatibleAttachments",
    "PreinstalledAttachmentsItemPrototypeSIDs",
    "PreinstalledUpgrades",
    "WeaponReloadTimePerAttachment",
}


def group_by_top_field(diffs: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[str, list[dict[str, object]]] = defaultdict(list)
    for entry in diffs:
        groups[top_field(entry)].append(entry)
    return [{"field": field, "changes": changes} for field, changes in sorted(groups.items())]


def build_reference_index() -> tuple[dict[str, tuple[Path, dict[str, list[str]]]], list[str]]:
    index: dict[str, tuple[Path, dict[str, list[str]]]] = {}
    scanned: list[str] = []
    for path in sorted(VANILLA_ROOT.rglob("*.cfg")):
        try:
            blocks = top_level_blocks(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        scanned.append(str(path.relative_to(VANILLA_ROOT)))
        for sid in blocks:
            index.setdefault(sid, (path, blocks))
    return index, scanned


def resolve_effective(sid: str, index: dict[str, tuple[Path, dict[str, list[str]]]]) -> tuple[dict[str, object], list[str], str | None]:
    source = index.get(sid)
    if not source:
        return {}, [], None
    path, blocks = source
    props, chain = effective_properties(sid, blocks)
    return props, chain, str(path.relative_to(VANILLA_ROOT))


def resolve_reference_pair(base_sid: object, unique_sid: object, index: dict[str, tuple[Path, dict[str, list[str]]]]) -> dict[str, object]:
    result: dict[str, object] = {"base_sid": base_sid, "unique_sid": unique_sid}
    if not isinstance(base_sid, str) or not isinstance(unique_sid, str):
        result.update({"resolved": False, "reason": "missing_reference_sid"}); return result
    base_source = index.get(base_sid); unique_source = index.get(unique_sid)
    if not base_source or not unique_source:
        result.update({"resolved": False, "reason": "reference_definition_not_present_in_vanilla_reference", "base_definition_found": bool(base_source), "unique_definition_found": bool(unique_source)})
        return result
    base_path, base_blocks = base_source; unique_path, unique_blocks = unique_source
    base_props, base_chain = effective_properties(base_sid, base_blocks); unique_props, unique_chain = effective_properties(unique_sid, unique_blocks)
    result.update({"resolved": True, "base_source": str(base_path.relative_to(VANILLA_ROOT)), "unique_source": str(unique_path.relative_to(VANILLA_ROOT)), "base_inheritance_chain": base_chain, "unique_inheritance_chain": unique_chain, "leaf_diffs": leaf_diff(base_props, unique_props)})
    return result


def player_attribute_sids(entry: dict[str, object]) -> tuple[object, object]:
    weapon = entry.get("weapon_prototype", {})
    if not isinstance(weapon, dict): return None, None
    diff = weapon.get("effective_diff_vs_base", {})
    if isinstance(diff, dict):
        player = diff.get("PlayerWeaponAttributes")
        if isinstance(player, dict): return player.get("base"), player.get("unique")
    return None, None


def equipment_identity_from_diffs(diffs: list[dict[str, object]]) -> dict[str, object]:
    selected = [diff for diff in diffs if top_field(diff) in EQUIPMENT_FIELDS]
    return {"fields": sorted({top_field(diff) for diff in selected}), "groups": group_by_top_field(selected), "leaf_diffs": selected}


def equipment_identity(entry: dict[str, object]) -> dict[str, object]:
    weapon = entry.get("weapon_prototype", {})
    diffs = weapon.get("leaf_diff_vs_base", []) if isinstance(weapon, dict) else []
    return equipment_identity_from_diffs(diffs)


def load_base_families() -> dict[tuple[str, str], dict]:
    result = {}
    for class_name, path in CLASS_CONFIGS.items():
        config = json.loads(path.read_text(encoding="utf-8"))
        for family_name, family in config.get("families", {}).items():
            result[(class_name, family_name)] = family
    return result


def build_dlc_context(reference_index: dict[str, tuple[Path, dict[str, list[str]]]]) -> tuple[dict[str, object], list[dict[str, object]]]:
    registry = json.loads(DLC_REGISTRY.read_text(encoding="utf-8")); families = load_base_families(); entries = {}; unresolved = []
    for name, weapon in registry.get("weapons", {}).items():
        pack = weapon["content_pack"]; class_name = weapon["class"]; base_name = weapon["base_family"]
        base = families.get((class_name, base_name))
        if not base:
            unresolved.append({"weapon": name, "content_pack": pack, "reason": "base_family_not_found", "class": class_name, "base_family": base_name}); continue
        dlc_setup_sid = weapon["general_setup_sid"]; base_setup_sid = base["general_setup_sid"]
        dlc_setup, dlc_setup_chain, dlc_setup_source = resolve_effective(dlc_setup_sid, reference_index); base_setup, base_setup_chain, base_setup_source = resolve_effective(base_setup_sid, reference_index)
        if not dlc_setup or not base_setup:
            unresolved.append({"weapon": name, "content_pack": pack, "reason": "general_setup_not_found", "dlc_general_setup_sid": dlc_setup_sid, "base_general_setup_sid": base_setup_sid}); continue
        setup_diffs = leaf_diff(base_setup, dlc_setup)
        dlc_weapon_sid = weapon.get("weapon_sid")
        weapon_diffs: list[dict[str, object]] = []; dlc_weapon_chain: list[str] = []; base_weapon_chain: list[str] = []; dlc_weapon_source = None; base_weapon_source = None
        base_weapon_sid = base.get("weapon_sid")
        if isinstance(dlc_weapon_sid, str) and isinstance(base_weapon_sid, str):
            dlc_weapon, dlc_weapon_chain, dlc_weapon_source = resolve_effective(dlc_weapon_sid, reference_index); base_weapon, base_weapon_chain, base_weapon_source = resolve_effective(base_weapon_sid, reference_index)
            if dlc_weapon and base_weapon: weapon_diffs = leaf_diff(base_weapon, dlc_weapon)
        all_diffs = setup_diffs + weapon_diffs
        gameplay = [diff for diff in all_diffs if top_field(diff) in GAMEPLAY_FIELDS and top_field(diff) != "PlayerWeaponAttributes"]
        equipment = equipment_identity_from_diffs(weapon_diffs)
        base_attr = base_setup.get("PlayerWeaponAttributes"); dlc_attr = dlc_setup.get("PlayerWeaponAttributes")
        if base_attr == dlc_attr: base_attr = dlc_attr = None
        entries[name] = {
            "content_pack": pack, "class": class_name, "base_family": base_name,
            "dlc_general_setup_sid": dlc_setup_sid, "base_general_setup_sid": base_setup_sid,
            "dlc_weapon_sid": dlc_weapon_sid, "base_weapon_sid": base_weapon_sid,
            "gameplay_identity": {"fields": sorted({top_field(diff) for diff in gameplay}), "groups": group_by_top_field(gameplay), "leaf_diffs": gameplay},
            "equipment_identity": equipment,
            "player_weapon_attributes": resolve_reference_pair(base_attr, dlc_attr, reference_index),
            "general_setup": {"dlc_source": dlc_setup_source, "base_source": base_setup_source, "dlc_inheritance_chain": dlc_setup_chain, "base_inheritance_chain": base_setup_chain, "leaf_diff_vs_base": setup_diffs},
            "weapon_prototype": {"dlc_source": dlc_weapon_source, "base_source": base_weapon_source, "dlc_inheritance_chain": dlc_weapon_chain, "base_inheritance_chain": base_weapon_chain, "leaf_diff_vs_base": weapon_diffs},
        }
    return entries, unresolved


def build_report() -> dict[str, object]:
    from analyze_unique_weapons import analyze
    base_report = analyze(); reference_index, scanned = build_reference_index(); uniques = {}; resolved_attributes = 0
    for name, entry in base_report["uniques"].items():
        base_attr, unique_attr = player_attribute_sids(entry); attributes = resolve_reference_pair(base_attr, unique_attr, reference_index)
        if attributes.get("resolved"): resolved_attributes += 1
        gameplay = entry["gameplay_signature_candidate"]; gameplay_without_ref = [diff for diff in gameplay["leaf_diffs"] if top_field(diff) != "PlayerWeaponAttributes"]
        uniques[name] = {"class": entry["class"], "base_family": entry["base_family"], "unique_weapon_sid": entry["unique_weapon_sid"], "base_weapon_sid": entry["base_weapon_sid"], "gameplay_identity": {"fields": sorted({top_field(diff) for diff in gameplay_without_ref}), "groups": group_by_top_field(gameplay_without_ref), "leaf_diffs": gameplay_without_ref}, "equipment_identity": equipment_identity(entry), "player_weapon_attributes": attributes}
    dlc_weapons, dlc_unresolved = build_dlc_context(reference_index)
    return {
        "summary": {"uniques": len(uniques), "dlc_weapons": len(dlc_weapons), "dlc_unresolved": len(dlc_unresolved), "player_attribute_pairs_resolved": resolved_attributes, "player_attribute_pairs_unresolved": len(uniques) - resolved_attributes, "vanilla_cfg_files_scanned": len(scanned)},
        "notes": ["gameplay_identity contains direct weapon/setup gameplay differences but omits the opaque PlayerWeaponAttributes SID itself.", "equipment_identity keeps attachment/preinstalled-upgrade differences separately because they can be the primary identity of a weapon variant.", "DLC weapons are compared against the BPRUE base_family from dlc_weapons.json while resolving definitions from VanillaReference/DLCGameData/<pack> and BaseGame references.", "player_weapon_attributes is resolved only when both referenced prototype definitions exist in the checked-in VanillaReference CFGs; missing source data is reported, never guessed."],
        "vanilla_reference_files_scanned": scanned, "uniques": uniques, "dlc_weapons": dlc_weapons, "dlc_unresolved": dlc_unresolved,
    }


def format_change(change: dict[str, object]) -> str:
    suffix = ""; delta = change.get("numeric_delta")
    if isinstance(delta, dict) and "percent" in delta: suffix = f" ({delta['percent']:+.1f}%)"
    return f"      {change['path']}: {change.get('base')} -> {change.get('unique')}{suffix}"


def print_group(title: str, identity: dict[str, object]) -> None:
    fields = identity.get("fields", []); print(f"  {title}: {', '.join(fields) if fields else '(none)'}")
    for group in identity.get("groups", []):
        print(f"    {group['field']}:")
        for change in group["changes"]: print(format_change(change))


def print_entry(name: str, entry: dict[str, object], label: str) -> None:
    pack = f"/{entry['content_pack']}" if "content_pack" in entry else ""
    print(f"\n{name} [{entry['class']}{pack}] <- {entry['base_family']} ({label})")
    print_group("Gameplay", entry["gameplay_identity"]); print_group("Equipment", entry["equipment_identity"])
    attrs = entry["player_weapon_attributes"]
    if attrs.get("resolved"):
        print(f"  PlayerWeaponAttributes: resolved ({len(attrs.get('leaf_diffs', []))} leaf diffs)")
        for diff in attrs.get("leaf_diffs", []): print(format_change(diff))
    elif attrs.get("base_sid") or attrs.get("unique_sid"):
        print(f"  PlayerWeaponAttributes: {attrs.get('base_sid')} -> {attrs.get('unique_sid')} [unresolved: {attrs.get('reason')}]")
    else: print("  PlayerWeaponAttributes: unchanged/not referenced by diff")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build signature-design context for BaseGame Unique and DLC weapons.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--print", action="store_true", dest="print_context", help="Print BaseGame Unique and DLC signature context.")
    parser.add_argument("--dlc-only", action="store_true", help="Print only DLC weapon comparisons (implies --print).")
    args = parser.parse_args(); report = build_report(); ensure_reports_dir(); args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(f"Signature context: uniques={summary['uniques']} | DLC weapons={summary['dlc_weapons']} | DLC unresolved={summary['dlc_unresolved']} | player attributes resolved={summary['player_attribute_pairs_resolved']}")
    print(f"Report: {args.output}")
    if args.print_context and not args.dlc_only:
        for name, entry in report["uniques"].items(): print_entry(name, entry, "BaseGame Unique")
    if args.print_context or args.dlc_only:
        for name, entry in report["dlc_weapons"].items(): print_entry(name, entry, "DLC weapon")
        if report["dlc_unresolved"]:
            print("\nUnresolved DLC weapons:")
            for entry in report["dlc_unresolved"]: print(f"  {entry}")


if __name__ == "__main__": main()
