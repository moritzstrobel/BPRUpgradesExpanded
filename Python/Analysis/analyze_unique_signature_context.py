from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from analyze_unique_weapons import VANILLA_ROOT, analyze, top_field, top_level_blocks, direct_properties, effective_properties, leaf_diff
from analysis_paths import ensure_reports_dir

DEFAULT_OUTPUT = Path(__file__).resolve().parent / "Reports" / "unique_signature_context.json"
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
    """Index top-level prototype SIDs from the checked-in VanillaReference CFGs.

    PlayerWeaponAttributes are references. If their definitions are present in a
    future VanillaReference dump this lets the analysis resolve them without a
    hard-coded filename. If they are not present, the report says so explicitly.
    """
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


def resolve_reference_pair(base_sid: object, unique_sid: object, index: dict[str, tuple[Path, dict[str, list[str]]]]) -> dict[str, object]:
    result: dict[str, object] = {"base_sid": base_sid, "unique_sid": unique_sid}
    if not isinstance(base_sid, str) or not isinstance(unique_sid, str):
        result.update({"resolved": False, "reason": "missing_reference_sid"}); return result
    base_source = index.get(base_sid); unique_source = index.get(unique_sid)
    if not base_source or not unique_source:
        result.update({
            "resolved": False,
            "reason": "reference_definition_not_present_in_vanilla_reference",
            "base_definition_found": bool(base_source),
            "unique_definition_found": bool(unique_source),
        })
        return result
    base_path, base_blocks = base_source; unique_path, unique_blocks = unique_source
    base_props, base_chain = effective_properties(base_sid, base_blocks)
    unique_props, unique_chain = effective_properties(unique_sid, unique_blocks)
    result.update({
        "resolved": True,
        "base_source": str(base_path.relative_to(VANILLA_ROOT)),
        "unique_source": str(unique_path.relative_to(VANILLA_ROOT)),
        "base_inheritance_chain": base_chain,
        "unique_inheritance_chain": unique_chain,
        "leaf_diffs": leaf_diff(base_props, unique_props),
    })
    return result


def player_attribute_sids(entry: dict[str, object]) -> tuple[object, object]:
    weapon = entry.get("weapon_prototype", {})
    if not isinstance(weapon, dict): return None, None
    diff = weapon.get("effective_diff_vs_base", {})
    if isinstance(diff, dict):
        player = diff.get("PlayerWeaponAttributes")
        if isinstance(player, dict): return player.get("base"), player.get("unique")
    return None, None


def equipment_identity(entry: dict[str, object]) -> dict[str, object]:
    weapon = entry.get("weapon_prototype", {})
    diffs = weapon.get("leaf_diff_vs_base", []) if isinstance(weapon, dict) else []
    selected = [diff for diff in diffs if top_field(diff) in EQUIPMENT_FIELDS]
    return {
        "fields": sorted({top_field(diff) for diff in selected}),
        "groups": group_by_top_field(selected),
        "leaf_diffs": selected,
    }


def build_report() -> dict[str, object]:
    base_report = analyze(); reference_index, scanned = build_reference_index(); uniques = {}
    resolved_attributes = 0
    for name, entry in base_report["uniques"].items():
        base_attr, unique_attr = player_attribute_sids(entry)
        attributes = resolve_reference_pair(base_attr, unique_attr, reference_index)
        if attributes.get("resolved"): resolved_attributes += 1
        gameplay = entry["gameplay_signature_candidate"]
        gameplay_without_ref = [diff for diff in gameplay["leaf_diffs"] if top_field(diff) != "PlayerWeaponAttributes"]
        uniques[name] = {
            "class": entry["class"],
            "base_family": entry["base_family"],
            "unique_weapon_sid": entry["unique_weapon_sid"],
            "base_weapon_sid": entry["base_weapon_sid"],
            "gameplay_identity": {
                "fields": sorted({top_field(diff) for diff in gameplay_without_ref}),
                "groups": group_by_top_field(gameplay_without_ref),
                "leaf_diffs": gameplay_without_ref,
            },
            "equipment_identity": equipment_identity(entry),
            "player_weapon_attributes": attributes,
        }
    return {
        "summary": {
            "uniques": len(uniques),
            "player_attribute_pairs_resolved": resolved_attributes,
            "player_attribute_pairs_unresolved": len(uniques) - resolved_attributes,
            "vanilla_cfg_files_scanned": len(scanned),
        },
        "notes": [
            "gameplay_identity contains direct weapon/setup gameplay differences but omits the opaque PlayerWeaponAttributes SID itself.",
            "equipment_identity keeps attachment/preinstalled-upgrade differences separately because they can be the primary Vanilla identity of a Unique.",
            "player_weapon_attributes is resolved only when both referenced prototype definitions exist in the checked-in VanillaReference CFGs; missing source data is reported, never guessed.",
        ],
        "vanilla_reference_files_scanned": scanned,
        "uniques": uniques,
    }


def format_change(change: dict[str, object]) -> str:
    suffix = ""; delta = change.get("numeric_delta")
    if isinstance(delta, dict) and "percent" in delta: suffix = f" ({delta['percent']:+.1f}%)"
    return f"      {change['path']}: {change.get('base')} -> {change.get('unique')}{suffix}"


def print_group(title: str, identity: dict[str, object]) -> None:
    fields = identity.get("fields", [])
    print(f"  {title}: {', '.join(fields) if fields else '(none)'}")
    for group in identity.get("groups", []):
        print(f"    {group['field']}:")
        for change in group["changes"]: print(format_change(change))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build signature-design context for Vanilla Unique weapons.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--print", action="store_true", dest="print_context", help="Print gameplay, equipment and PlayerWeaponAttributes context.")
    args = parser.parse_args(); report = build_report(); ensure_reports_dir()
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = report["summary"]
    print(f"Unique signature context: uniques={summary['uniques']} | player attributes resolved={summary['player_attribute_pairs_resolved']} | unresolved={summary['player_attribute_pairs_unresolved']}")
    print(f"Report: {args.output}")
    if args.print_context:
        for name, entry in report["uniques"].items():
            print(f"\n{name} [{entry['class']}] <- {entry['base_family']}")
            print_group("Gameplay", entry["gameplay_identity"])
            print_group("Equipment", entry["equipment_identity"])
            attrs = entry["player_weapon_attributes"]
            if attrs.get("resolved"):
                print(f"  PlayerWeaponAttributes: resolved ({len(attrs.get('leaf_diffs', []))} leaf diffs)")
                for diff in attrs.get("leaf_diffs", []): print(format_change(diff))
            elif attrs.get("base_sid") or attrs.get("unique_sid"):
                print(f"  PlayerWeaponAttributes: {attrs.get('base_sid')} -> {attrs.get('unique_sid')} [unresolved: {attrs.get('reason')}]")
            else:
                print("  PlayerWeaponAttributes: unchanged/not referenced by diff")


if __name__ == "__main__":
    main()
