from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from analyze_unique_weapons import (
    CLASS_CONFIGS, GAMEPLAY_FIELDS, VANILLA_ROOT, deep_merge, direct_properties,
    leaf_diff, refkey, top_field, top_level_blocks,
)
from analysis_paths import ensure_reports_dir

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "Reports" / "unique_signature_context.json"
CFG_ROOT = Path(__file__).resolve().parent.parent / "CFGGenerators"
DLC_REGISTRY = CFG_ROOT / "Common" / "dlc_weapons.json"
EQUIPMENT_FIELDS = {"CompatibleAttachments", "PreinstalledAttachmentsItemPrototypeSIDs", "PreinstalledUpgrades", "WeaponReloadTimePerAttachment"}
REFURL_RE = re.compile(r"(?:\{|;)refurl=([^;}]+)")
Reference = tuple[Path, dict[str, list[str]]]
ReferenceIndex = dict[str, list[Reference]]


def group_by_top_field(diffs):
    groups = defaultdict(list)
    for entry in diffs: groups[top_field(entry)].append(entry)
    return [{"field": field, "changes": changes} for field, changes in sorted(groups.items())]


def refurl(block):
    if not block: return None
    match = REFURL_RE.search(block[0]); return match.group(1).strip() if match else None


def build_reference_index():
    index = defaultdict(list); files = {}; scanned = []
    root = VANILLA_ROOT.resolve()
    for path in sorted(VANILLA_ROOT.rglob("*.cfg")):
        try: blocks = top_level_blocks(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError): continue
        path = path.resolve(); files[path] = blocks; scanned.append(str(path.relative_to(root)))
        for sid in blocks: index[sid].append((path, blocks))
    return dict(index), files, scanned


def choose_source(sid, index, preferred_file=None, preferred_basename=None, preferred_pack=None):
    candidates = index.get(sid, [])
    if preferred_file is not None:
        wanted = preferred_file.resolve()
        exact = [candidate for candidate in candidates if candidate[0] == wanted]
        if exact: return exact[0]
        return None
    filtered = candidates
    if preferred_pack:
        marker = f"DLCGameData/{preferred_pack}/"
        filtered = [candidate for candidate in filtered if marker in candidate[0].as_posix()]
    if preferred_basename:
        filtered = [candidate for candidate in filtered if candidate[0].name == preferred_basename]
    if filtered: return filtered[0]
    return candidates[0] if candidates and not (preferred_basename or preferred_pack) else None


def resolve_refurl_path(current_path, raw_refurl, files):
    normalized = raw_refurl.replace("\\", "/")
    literal = (current_path.parent / normalized).resolve()
    if literal in files: return literal
    basename = Path(normalized).name
    matches = [path for path in files if path.name == basename]
    if len(matches) == 1: return matches[0]
    if "GameData/" in normalized and "DLCGameData/" not in normalized:
        base_matches = [path for path in matches if "DLCGameData/" not in path.as_posix()]
        if len(base_matches) == 1: return base_matches[0]
    return None


def resolve_effective_from_source(sid, source, index, files, seen=None):
    path, blocks = source; block = blocks.get(sid)
    if not block: return {}, [], [{"sid": sid, "reason": "sid_not_found_in_selected_source", "source": str(path)}]
    seen = set() if seen is None else set(seen); key = (path, sid)
    if key in seen: return {}, [sid], [{"sid": sid, "reason": "inheritance_cycle", "source": str(path)}]
    seen.add(key); result = {}; chain = [sid]; unresolved = []
    parent_sid = refkey(block)
    if parent_sid and not parent_sid.startswith("["):
        parent_source = None; raw = refurl(block)
        if raw:
            parent_path = resolve_refurl_path(path, raw, files)
            if parent_path is not None: parent_source = choose_source(parent_sid, index, preferred_file=parent_path)
            if parent_source is None:
                unresolved.append({"sid": parent_sid, "reason": "refurl_target_or_parent_missing", "refurl": raw, "from_source": str(path.relative_to(VANILLA_ROOT.resolve()))})
        else:
            parent_source = choose_source(parent_sid, index, preferred_file=path) or choose_source(parent_sid, index)
        if parent_source is not None:
            parent_props, parent_chain, parent_missing = resolve_effective_from_source(parent_sid, parent_source, index, files, seen)
            result = parent_props; chain.extend(parent_chain); unresolved.extend(parent_missing)
    result = deep_merge(result, direct_properties(block))
    return result, chain, unresolved


def resolve_effective(sid, index, files, preferred_basename=None, preferred_pack=None):
    source = choose_source(sid, index, preferred_basename=preferred_basename, preferred_pack=preferred_pack)
    if not source: return {}, [], None, [{"sid": sid, "reason": "definition_not_present_in_vanilla_reference"}]
    props, chain, missing = resolve_effective_from_source(sid, source, index, files)
    return props, chain, str(source[0].relative_to(VANILLA_ROOT.resolve())), missing


def resolve_reference_pair(base_sid, unique_sid, index, files, preferred_basename=None, *, base_basename=None, unique_basename=None, unique_pack=None):
    result = {"base_sid": base_sid, "unique_sid": unique_sid}
    if not isinstance(base_sid, str) or not isinstance(unique_sid, str):
        result.update({"resolved": False, "reason": "missing_reference_sid"}); return result
    base_file = base_basename or preferred_basename
    unique_file = unique_basename or preferred_basename
    base_props, base_chain, base_source, base_missing = resolve_effective(base_sid, index, files, preferred_basename=base_file)
    unique_props, unique_chain, unique_source, unique_missing = resolve_effective(unique_sid, index, files, preferred_basename=unique_file, preferred_pack=unique_pack)
    if not base_source or not unique_source:
        result.update({"resolved": False, "reason": "reference_definition_not_present_in_vanilla_reference", "base_definition_found": bool(base_source), "unique_definition_found": bool(unique_source), "unresolved_inheritance": base_missing + unique_missing}); return result
    missing = base_missing + unique_missing
    result.update({"resolved": not missing, "reason": None if not missing else "inheritance_source_missing", "base_source": base_source, "unique_source": unique_source, "base_inheritance_chain": base_chain, "unique_inheritance_chain": unique_chain, "unresolved_inheritance": missing, "leaf_diffs": leaf_diff(base_props, unique_props)})
    return result


def player_attribute_sids(entry):
    weapon = entry.get("weapon_prototype", {})
    if not isinstance(weapon, dict): return None, None
    diff = weapon.get("effective_diff_vs_base", {})
    player = diff.get("PlayerWeaponAttributes") if isinstance(diff, dict) else None
    return (player.get("base"), player.get("unique")) if isinstance(player, dict) else (None, None)


def equipment_identity_from_diffs(diffs):
    selected = [d for d in diffs if top_field(d) in EQUIPMENT_FIELDS]
    return {"fields": sorted({top_field(d) for d in selected}), "groups": group_by_top_field(selected), "leaf_diffs": selected}


def equipment_identity(entry):
    weapon = entry.get("weapon_prototype", {}); diffs = weapon.get("leaf_diff_vs_base", []) if isinstance(weapon, dict) else []
    return equipment_identity_from_diffs(diffs)


def load_base_families():
    result = {}
    for class_name, path in CLASS_CONFIGS.items():
        config = json.loads(path.read_text(encoding="utf-8"))
        for family_name, family in config.get("families", {}).items(): result[(class_name, family_name)] = family
    return result


def absolute_identity(props, allowed_fields):
    values = {field: props[field] for field in sorted(allowed_fields) if field in props}
    return {"fields": list(values), "values": values}


def find_weapon_for_setup(setup_sid, pack, index):
    marker = f"DLCGameData/{pack}/"; candidates = []
    for sid, sources in index.items():
        for path, blocks in sources:
            if marker not in path.as_posix() or path.name != "ItemPrototypes.cfg": continue
            block = blocks.get(sid)
            if block and direct_properties(block).get("GeneralWeaponSetup") == setup_sid: candidates.append(sid)
    unique = sorted(set(candidates)); return unique[0] if len(unique) == 1 else None


def build_dlc_context(index, files):
    registry = json.loads(DLC_REGISTRY.read_text(encoding="utf-8")); families = load_base_families(); entries = {}; unresolved = []
    for name, weapon in registry.get("weapons", {}).items():
        pack, class_name, base_name = weapon["content_pack"], weapon["class"], weapon["base_family"]
        base = families.get((class_name, base_name))
        if not base: unresolved.append({"weapon": name, "reason": "base_family_not_found"}); continue
        standalone = bool(weapon.get("standalone", False)); comparison_base = weapon.get("comparison_base", base_name); dlc_setup_sid = weapon["general_setup_sid"]
        dlc_setup, dlc_setup_chain, dlc_setup_source, dlc_setup_missing = resolve_effective(dlc_setup_sid, index, files, preferred_basename="WeaponGeneralSetupPrototypes.cfg", preferred_pack=pack)
        if not dlc_setup: unresolved.append({"weapon": name, "reason": "general_setup_not_found"}); continue
        dlc_weapon_sid = weapon.get("weapon_sid") or find_weapon_for_setup(dlc_setup_sid, pack, index)
        dlc_weapon = {}; dlc_weapon_chain = []; dlc_weapon_source = None; dlc_weapon_missing = []
        if isinstance(dlc_weapon_sid, str): dlc_weapon, dlc_weapon_chain, dlc_weapon_source, dlc_weapon_missing = resolve_effective(dlc_weapon_sid, index, files, preferred_basename="ItemPrototypes.cfg", preferred_pack=pack)
        if standalone or comparison_base is None:
            entries[name] = {"content_pack": pack, "class": class_name, "base_family": base_name, "comparison_mode": "standalone", "comparison_base": None, "dlc_general_setup_sid": dlc_setup_sid, "base_general_setup_sid": None, "dlc_weapon_sid": dlc_weapon_sid, "base_weapon_sid": None, "gameplay_identity": absolute_identity(dlc_setup, GAMEPLAY_FIELDS), "equipment_identity": absolute_identity(dlc_weapon, EQUIPMENT_FIELDS), "player_weapon_attributes": {"base_sid": None, "unique_sid": dlc_weapon.get("PlayerWeaponAttributes"), "resolved": False, "reason": "standalone_no_comparison_base"}, "general_setup": {"dlc_source": dlc_setup_source, "dlc_inheritance_chain": dlc_setup_chain, "unresolved_inheritance": dlc_setup_missing, "absolute_values": dlc_setup}, "weapon_prototype": {"dlc_source": dlc_weapon_source, "dlc_inheritance_chain": dlc_weapon_chain, "unresolved_inheritance": dlc_weapon_missing, "absolute_values": dlc_weapon}}
            continue
        comparison_family = families.get((class_name, str(comparison_base)))
        if not comparison_family: unresolved.append({"weapon": name, "reason": "comparison_base_not_found"}); continue
        base_setup_sid = comparison_family["general_setup_sid"]
        base_setup, base_setup_chain, base_setup_source, base_setup_missing = resolve_effective(base_setup_sid, index, files, preferred_basename="WeaponGeneralSetupPrototypes.cfg")
        base_weapon_sid = comparison_family.get("weapon_sid"); base_weapon = {}; base_weapon_chain = []; base_weapon_source = None; base_weapon_missing = []
        if isinstance(base_weapon_sid, str): base_weapon, base_weapon_chain, base_weapon_source, base_weapon_missing = resolve_effective(base_weapon_sid, index, files, preferred_basename="WeaponPrototypes.cfg")
        setup_diffs = leaf_diff(base_setup, dlc_setup); weapon_diffs = leaf_diff(base_weapon, dlc_weapon) if base_weapon and dlc_weapon else []; all_diffs = setup_diffs + weapon_diffs
        gameplay = [d for d in all_diffs if top_field(d) in GAMEPLAY_FIELDS and top_field(d) != "PlayerWeaponAttributes"]
        base_attr, dlc_attr = base_weapon.get("PlayerWeaponAttributes"), dlc_weapon.get("PlayerWeaponAttributes")
        if base_attr == dlc_attr: base_attr = dlc_attr = None
        attributes = resolve_reference_pair(
            base_attr, dlc_attr, index, files,
            base_basename="PlayerWeaponAttributesPrototypes.cfg",
            unique_basename="WeaponAttributesPrototypes.cfg",
            unique_pack=pack,
        )
        entries[name] = {"content_pack": pack, "class": class_name, "base_family": base_name, "comparison_mode": "relative", "comparison_base": comparison_base, "dlc_general_setup_sid": dlc_setup_sid, "base_general_setup_sid": base_setup_sid, "dlc_weapon_sid": dlc_weapon_sid, "base_weapon_sid": base_weapon_sid, "gameplay_identity": {"fields": sorted({top_field(d) for d in gameplay}), "groups": group_by_top_field(gameplay), "leaf_diffs": gameplay}, "equipment_identity": equipment_identity_from_diffs(weapon_diffs), "player_weapon_attributes": attributes, "general_setup": {"dlc_source": dlc_setup_source, "base_source": base_setup_source, "dlc_inheritance_chain": dlc_setup_chain, "base_inheritance_chain": base_setup_chain, "unresolved_inheritance": dlc_setup_missing + base_setup_missing, "leaf_diff_vs_base": setup_diffs}, "weapon_prototype": {"dlc_source": dlc_weapon_source, "base_source": base_weapon_source, "dlc_inheritance_chain": dlc_weapon_chain, "base_inheritance_chain": base_weapon_chain, "unresolved_inheritance": dlc_weapon_missing + base_weapon_missing, "leaf_diff_vs_base": weapon_diffs}}
    return entries, unresolved


def build_report():
    from analyze_unique_weapons import analyze
    base_report = analyze(); index, files, scanned = build_reference_index(); uniques = {}; base_resolved = 0
    for name, entry in base_report["uniques"].items():
        base_attr, unique_attr = player_attribute_sids(entry); attributes = resolve_reference_pair(base_attr, unique_attr, index, files)
        if attributes.get("resolved"): base_resolved += 1
        gameplay = entry["gameplay_signature_candidate"]; clean = [d for d in gameplay["leaf_diffs"] if top_field(d) != "PlayerWeaponAttributes"]
        uniques[name] = {"class": entry["class"], "base_family": entry["base_family"], "unique_weapon_sid": entry["unique_weapon_sid"], "base_weapon_sid": entry["base_weapon_sid"], "gameplay_identity": {"fields": sorted({top_field(d) for d in clean}), "groups": group_by_top_field(clean), "leaf_diffs": clean}, "equipment_identity": equipment_identity(entry), "player_weapon_attributes": attributes}
    dlc_weapons, dlc_unresolved = build_dlc_context(index, files)
    standalone_count = sum(1 for e in dlc_weapons.values() if e.get("comparison_mode") == "standalone")
    dlc_resolved = sum(1 for e in dlc_weapons.values() if e.get("player_weapon_attributes", {}).get("resolved"))
    return {"summary": {"uniques": len(uniques), "dlc_weapons": len(dlc_weapons), "dlc_standalone": standalone_count, "dlc_unresolved": len(dlc_unresolved), "basegame_player_attribute_pairs_resolved": base_resolved, "dlc_player_attribute_pairs_resolved": dlc_resolved, "vanilla_cfg_files_scanned": len(scanned)}, "notes": ["DLC inheritance follows refkey/refurl across checked-in VanillaReference CFG files.", "Duplicate SIDs are source-aware; DLC lookups constrain both content pack and prototype file domain.", "DLC PlayerWeaponAttributes compare BaseGame PlayerWeaponAttributesPrototypes.cfg against the content pack's WeaponAttributesPrototypes.cfg.", "DLC ItemPrototypes are discovered from GeneralWeaponSetup when weapon_sid is not explicitly registered.", "base_family controls BPRUE module inheritance; comparison_base independently controls signature analysis.", "Missing cross-file sources are reported in unresolved_inheritance instead of silently producing misleading None diffs."], "vanilla_reference_files_scanned": scanned, "uniques": uniques, "dlc_weapons": dlc_weapons, "dlc_unresolved": dlc_unresolved}


def format_change(change):
    suffix = ""; delta = change.get("numeric_delta")
    if isinstance(delta, dict) and "percent" in delta: suffix = f" ({delta['percent']:+.1f}%)"
    return f"      {change['path']}: {change.get('base')} -> {change.get('unique')}{suffix}"


def print_group(title, identity):
    fields = identity.get("fields", []); print(f"  {title}: {', '.join(fields) if fields else '(none)'}")
    for group in identity.get("groups", []):
        print(f"    {group['field']}:")
        for change in group["changes"]: print(format_change(change))


def print_absolute_group(title, identity):
    fields = identity.get("fields", []); print(f"  {title} (absolute): {', '.join(fields) if fields else '(none)'}")
    for field, value in identity.get("values", {}).items(): print(f"    {field}: {value}")


def print_entry(name, entry, label):
    pack = f"/{entry['content_pack']}" if "content_pack" in entry else ""; mode = entry.get("comparison_mode", "relative")
    if mode == "standalone":
        print(f"\n{name} [{entry['class']}{pack}] (standalone DLC weapon; BPRUE modules <- {entry['base_family']})"); print_absolute_group("Gameplay", entry["gameplay_identity"]); print_absolute_group("Equipment", entry["equipment_identity"])
    else:
        base = entry.get("comparison_base", entry["base_family"]); print(f"\n{name} [{entry['class']}{pack}] <- {base} ({label}; BPRUE modules <- {entry['base_family']})"); print_group("Gameplay", entry["gameplay_identity"]); print_group("Equipment", entry["equipment_identity"])
    attrs = entry["player_weapon_attributes"]
    if attrs.get("resolved"):
        print(f"  PlayerWeaponAttributes: resolved ({len(attrs.get('leaf_diffs', []))} leaf diffs)")
        for diff in attrs.get("leaf_diffs", []): print(format_change(diff))
    elif attrs.get("unique_sid"):
        print(f"  PlayerWeaponAttributes: {attrs.get('base_sid')} -> {attrs.get('unique_sid')} [{attrs.get('reason')}]")
        for missing in attrs.get("unresolved_inheritance", []): print(f"    unresolved: {missing}")
    else: print("  PlayerWeaponAttributes: unchanged/not referenced by diff")
    for section_name in ("general_setup", "weapon_prototype"):
        section = entry.get(section_name, {})
        if isinstance(section, dict):
            for missing in section.get("unresolved_inheritance", []): print(f"  {section_name} unresolved: {missing}")


def main():
    parser = argparse.ArgumentParser(description="Build signature-design context for BaseGame Unique and DLC weapons."); parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--print", action="store_true", dest="print_context"); parser.add_argument("--dlc-only", action="store_true"); args = parser.parse_args()
    report = build_report(); ensure_reports_dir(); args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"); summary = report["summary"]
    print(f"Signature context: uniques={summary['uniques']} | DLC weapons={summary['dlc_weapons']} | standalone={summary['dlc_standalone']} | DLC unresolved={summary['dlc_unresolved']} | DLC player attributes resolved={summary['dlc_player_attribute_pairs_resolved']}"); print(f"Report: {args.output}")
    if args.print_context and not args.dlc_only:
        for name, entry in report["uniques"].items(): print_entry(name, entry, "BaseGame Unique")
    if args.print_context or args.dlc_only:
        for name, entry in report["dlc_weapons"].items(): print_entry(name, entry, "DLC weapon")
        if report["dlc_unresolved"]:
            print("\nUnresolved DLC weapons:")
            for entry in report["dlc_unresolved"]: print(f"  {entry}")


if __name__ == "__main__": main()
