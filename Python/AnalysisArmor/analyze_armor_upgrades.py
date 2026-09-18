#!/usr/bin/env python3
"""Analyze Vanilla armor upgrade topology and write machine-readable reports."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_ROOT = Path(__file__).resolve().parent
REPORT_DIR = ANALYSIS_ROOT / "Reports"
VANILLA = PYTHON_ROOT / "VanillaReference"
ARMOR_CFG = VANILLA / "ArmorPrototypes.cfg"
UPGRADE_CFG = VANILLA / "UpgradePrototypes.cfg"
EFFECT_CFG = VANILLA / "EffectPrototypes.cfg"
CLASSIFICATION_REPORT = REPORT_DIR / "armor_classification.json"

STRUCT_START = re.compile(r"^\s*([^/\s][^:]*)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?\s*$")
ARRAY_VALUE = re.compile(r"^\s*\[\d+\]\s*=\s*([^\s{]+)", re.MULTILINE)
SID_FIELD = re.compile(r"^\s*SID\s*=\s*([^\s]+)", re.MULTILINE)
FIELD_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*(?:\{[^}]*\})?\s*$")
NAMED_STRUCT = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*struct\.begin")

ESCAPE_TERMS = ("module", "socket", "attachment", "fitting", "preinstalled")
RELATION_TERMS = ("upgradeprototypesid", "effectprototypesid")
ARRAY_FIELDS = ("EffectPrototypeSIDs", "RequiredUpgradePrototypeSIDs", "BlockingUpgradePrototypeSIDs", "RequiredItemPrototypeSIDs")


def top_level_structs(text: str) -> dict[str, str]:
    lines = text.splitlines()
    result: dict[str, str] = {}
    i = 0
    while i < len(lines):
        match = STRUCT_START.match(lines[i])
        if not match:
            i += 1
            continue
        name = match.group(1).strip()
        depth = 1
        j = i + 1
        while j < len(lines) and depth:
            depth += lines[j].count("struct.begin")
            depth -= lines[j].count("struct.end")
            j += 1
        result[name] = "\n".join(lines[i:j])
        i = j
    return result


def extract_named_struct(block: str, field: str) -> str | None:
    lines = block.splitlines()
    start_re = re.compile(rf"^\s*{re.escape(field)}\s*:\s*struct\.begin")
    for i, line in enumerate(lines):
        if not start_re.match(line):
            continue
        depth = 1
        j = i + 1
        while j < len(lines) and depth:
            depth += lines[j].count("struct.begin")
            depth -= lines[j].count("struct.end")
            j += 1
        return "\n".join(lines[i:j])
    return None


def direct_fields(block: str) -> dict[str, list[str]]:
    """Return assignments/child-struct names that occur at top-level inside block."""
    lines = block.splitlines()
    fields: dict[str, list[str]] = defaultdict(list)
    depth = 0
    for line in lines[1:-1]:
        if depth == 0:
            sm = NAMED_STRUCT.match(line)
            if sm:
                fields[sm.group(1)].append("<struct>")
            else:
                fm = FIELD_LINE.match(line)
                if fm:
                    fields[fm.group(1)].append(fm.group(2).strip())
        depth += line.count("struct.begin")
        depth -= line.count("struct.end")
    return dict(fields)


def array_field_values(block: str, field: str) -> list[str]:
    nested = extract_named_struct(block, field)
    return [x for x in ARRAY_VALUE.findall(nested or "") if x != "empty"]


def scalar_field(block: str, field: str) -> str | None:
    values = direct_fields(block).get(field, [])
    return values[-1] if values else None


def load_player_classification() -> dict[str, dict[str, object]]:
    if not CLASSIFICATION_REPORT.exists():
        raise FileNotFoundError(
            f"{CLASSIFICATION_REPORT} is missing. Run classify_armor.py first."
        )
    payload = json.loads(CLASSIFICATION_REPORT.read_text(encoding="utf-8"))
    rows = {}
    for category_rows in payload.get("categories", {}).values():
        for row in category_rows:
            rows[row["sid"]] = row
    return rows


def matching_lines(block: str, terms: tuple[str, ...]) -> list[str]:
    result = []
    for line in block.splitlines():
        low = line.lower()
        if any(term in low for term in terms):
            result.append(line.strip())
    return result


def write_json(name: str, payload: object) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--armor", help="Only analyze armor SIDs containing this text")
    parser.add_argument("--details", action="store_true", help="Also print Armor -> Upgrade SIDs")
    args = parser.parse_args()

    armor_structs = top_level_structs(ARMOR_CFG.read_text(encoding="utf-8"))
    upgrade_structs = top_level_structs(UPGRADE_CFG.read_text(encoding="utf-8"))
    effect_structs = top_level_structs(EFFECT_CFG.read_text(encoding="utf-8"))

    classification = load_player_classification()
    armors = []
    referenced: set[str] = set()
    owners: dict[str, list[str]] = defaultdict(list)

    for name, block in armor_structs.items():
        sid_match = SID_FIELD.search(block)
        sid = sid_match.group(1) if sid_match else name
        if sid not in classification:
            continue
        if args.armor and args.armor.lower() not in sid.lower():
            continue
        arr = extract_named_struct(block, "UpgradePrototypeSIDs")
        upgrades = [x for x in ARRAY_VALUE.findall(arr or "") if x != "empty"]
        for upgrade in upgrades:
            owners[upgrade].append(sid)
        referenced.update(upgrades)
        meta = classification[sid]
        armors.append({
            "sid": sid,
            "category": meta["category"],
            "faction": meta["faction_candidate"],
            "upgrades": upgrades,
            "fields": direct_fields(block),
        })

    resolved = sorted(referenced.intersection(upgrade_structs))
    missing = sorted(referenced.difference(upgrade_structs))

    field_counts = Counter()
    field_examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    escape_hits = []
    relation_hits = []

    for sid in resolved:
        block = upgrade_structs[sid]
        fields = direct_fields(block)
        for field, values in fields.items():
            field_counts[field] += 1
            if len(field_examples[field]) < 8:
                field_examples[field].append({"sid": sid, "values": values})

        escape_lines = matching_lines(block, ESCAPE_TERMS)
        relation_lines = matching_lines(block, RELATION_TERMS)
        if escape_lines:
            escape_hits.append({"sid": sid, "armors": owners[sid], "lines": escape_lines})
        if relation_lines:
            relation_hits.append({"sid": sid, "armors": owners[sid], "lines": relation_lines})

    upgrade_details = {}
    modifications = []
    for sid in resolved:
        block = upgrade_structs[sid]
        detail = {
            "sid": sid,
            "owners": sorted(owners[sid]),
            "text": scalar_field(block, "Text"),
            "hint": scalar_field(block, "Hint"),
            "base_cost": scalar_field(block, "BaseCost"),
            "upgrade_target_part": scalar_field(block, "UpgradeTargetPart"),
            "vertical_position": scalar_field(block, "VerticalPosition"),
            "horizontal_position": scalar_field(block, "HorizontalPosition"),
            "is_modification": scalar_field(block, "IsModification") == "true",
        }
        for field in ARRAY_FIELDS:
            detail[field] = array_field_values(block, field)
        owner_meta = [classification[o] for o in owners[sid] if o in classification]
        detail["owner_categories"] = sorted({m["category"] for m in owner_meta})
        detail["owner_factions"] = sorted({m["faction_candidate"] for m in owner_meta})
        upgrade_details[sid] = detail
        if detail["is_modification"]:
            modifications.append(detail)

    modification_by_category = Counter(
        category for item in modifications for category in item["owner_categories"]
    )
    modification_by_faction = Counter(
        faction for item in modifications for faction in item["owner_factions"]
    )
    modification_effects = Counter(
        effect for item in modifications for effect in item["EffectPrototypeSIDs"]
    )
    modification_report = {
        "count": len(modifications),
        "by_armor_category": dict(sorted(modification_by_category.items())),
        "by_faction": dict(sorted(modification_by_faction.items())),
        "effect_sid_counts": dict(modification_effects.most_common()),
        "upgrades": sorted(modifications, key=lambda x: x["sid"]),
    }

    # Resolve the EffectPrototype layer used by the selected armor upgrades.
    referenced_effects = sorted({
        effect
        for detail in upgrade_details.values()
        for effect in detail["EffectPrototypeSIDs"]
    })
    resolved_effects = sorted(set(referenced_effects).intersection(effect_structs))
    missing_effects = sorted(set(referenced_effects).difference(effect_structs))

    effect_field_counts = Counter()
    effect_field_examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    effect_details = {}
    structural_groups: dict[str, list[str]] = defaultdict(list)

    for sid in resolved_effects:
        block = effect_structs[sid]
        fields = direct_fields(block)
        for field, values in fields.items():
            effect_field_counts[field] += 1
            if len(effect_field_examples[field]) < 8:
                effect_field_examples[field].append({"sid": sid, "values": values})

        used_by_upgrades = sorted(
            upgrade_sid
            for upgrade_sid, detail in upgrade_details.items()
            if sid in detail["EffectPrototypeSIDs"]
        )
        used_by_armors = sorted({
            owner
            for upgrade_sid in used_by_upgrades
            for owner in upgrade_details[upgrade_sid]["owners"]
        })

        # Group by field shape, not values. This exposes repeated GSC effect mechanisms
        # even when every armor has its own SID and tuning values.
        signature = tuple(sorted(fields.keys()))
        signature_key = "|".join(signature) if signature else "<no-direct-fields>"
        structural_groups[signature_key].append(sid)

        effect_details[sid] = {
            "sid": sid,
            "direct_fields": fields,
            "field_signature": list(signature),
            "used_by_upgrades": used_by_upgrades,
            "used_by_armors": used_by_armors,
            "owner_categories": sorted({
                classification[o]["category"] for o in used_by_armors if o in classification
            }),
            "owner_factions": sorted({
                classification[o]["faction_candidate"] for o in used_by_armors if o in classification
            }),
        }

    effect_inventory = [
        {"field": field, "count": count, "examples": effect_field_examples[field]}
        for field, count in effect_field_counts.most_common()
    ]
    effect_groups = [
        {
            "field_signature": [] if key == "<no-direct-fields>" else key.split("|"),
            "count": len(sids),
            "effect_sids": sorted(sids),
        }
        for key, sids in sorted(
            structural_groups.items(), key=lambda item: (-len(item[1]), item[0])
        )
    ]
    effect_report = {
        "referenced_effect_sids": len(referenced_effects),
        "resolved_effect_sids": len(resolved_effects),
        "missing_effect_sids": missing_effects,
        "distinct_direct_effect_fields": len(effect_field_counts),
        "structural_group_count": len(effect_groups),
        "field_inventory": effect_inventory,
        "structural_groups": effect_groups,
        "effects": effect_details,
    }

    inventory = [
        {"field": field, "count": count, "examples": field_examples[field]}
        for field, count in field_counts.most_common()
    ]

    summary = {
        "armor_structs_selected": len(armors),
        "referenced_upgrade_sids": len(referenced),
        "resolved_upgrade_sids": len(resolved),
        "missing_upgrade_sids": len(missing),
        "escape_term_upgrade_hits": len(escape_hits),
        "upgrade_field_count": len(field_counts),
        "filter": args.armor,
        "player_armor_only": True,
        "modification_upgrade_count": len(modifications),
        "referenced_effect_sids": len(referenced_effects),
        "resolved_effect_sids": len(resolved_effects),
        "missing_effect_sids": len(missing_effects),
        "effect_structural_groups": len(effect_groups),
    }

    write_json("armor_upgrade_summary.json", summary)
    write_json("armor_upgrade_field_inventory.json", inventory)
    write_json("armor_upgrade_escape_paths.json", escape_hits)
    write_json("armor_upgrade_relations.json", relation_hits)
    write_json("armor_upgrade_missing.json", missing)
    write_json("armor_upgrade_mapping.json", armors)
    write_json("armor_upgrade_details.json", upgrade_details)
    write_json("armor_modification_analysis.json", modification_report)
    write_json("armor_effect_analysis.json", effect_report)
    write_json("armor_effect_details.json", effect_details)

    print("=== BPRUE Vanilla Armor Upgrade Analysis ===")
    print(f"Armor structs selected: {len(armors)}")
    print(f"Referenced upgrade SIDs: {len(referenced)}")
    print(f"Resolved in UpgradePrototypes.cfg: {len(resolved)}")
    print(f"Missing from UpgradePrototypes.cfg: {len(missing)}")
    print(f"Distinct direct UpgradePrototype fields: {len(field_counts)}")
    print(f"Upgrade prototypes with module/escape-term hits: {len(escape_hits)}")
    print(f"IsModification=true upgrades: {len(modifications)}")
    print(f"Referenced EffectPrototype SIDs: {len(referenced_effects)}")
    print(f"Resolved in EffectPrototypes.cfg: {len(resolved_effects)}")
    print(f"Missing from EffectPrototypes.cfg: {len(missing_effects)}")
    print(f"Distinct direct EffectPrototype fields: {len(effect_field_counts)}")
    print(f"Effect structural groups: {len(effect_groups)}")

    print("\n=== Most common direct UpgradePrototype fields ===")
    for field, count in field_counts.most_common():
        print(f"{field}: {count}")

    print("\n=== IsModification=true by armor category ===")
    if modification_by_category:
        for category, count in sorted(modification_by_category.items()):
            print(f"{category}: {count}")
    else:
        print("None")

    print("\n=== IsModification=true by faction ===")
    if modification_by_faction:
        for faction, count in sorted(modification_by_faction.items()):
            print(f"{faction}: {count}")
    else:
        print("None")

    if modifications:
        print("\n=== Modification upgrades ===")
        for item in sorted(modifications, key=lambda x: x["sid"]):
            effects = ", ".join(item["EffectPrototypeSIDs"]) or "no effects"
            owners_text = ", ".join(item["owners"])
            print(f"{item['sid']}")
            print(f"  owners: {owners_text}")
            print(f"  effects: {effects}")
            if item["RequiredUpgradePrototypeSIDs"]:
                print("  requires: " + ", ".join(item["RequiredUpgradePrototypeSIDs"]))
            if item["BlockingUpgradePrototypeSIDs"]:
                print("  blocks: " + ", ".join(item["BlockingUpgradePrototypeSIDs"]))

    print("\n=== Most common direct EffectPrototype fields ===")
    for field, count in effect_field_counts.most_common():
        print(f"{field}: {count}")

    print("\n=== Most common EffectPrototype structures ===")
    for group in effect_groups[:20]:
        signature = ", ".join(group["field_signature"]) or "<no direct fields>"
        print(f"{group['count']}x: {signature}")
        for sid in group["effect_sids"][:5]:
            print(f"  {sid}")
        if len(group["effect_sids"]) > 5:
            print(f"  ... {len(group['effect_sids']) - 5} more")

    if missing_effects:
        print("\n=== Dangling Vanilla Effect References ===")
        for sid in missing_effects:
            print(sid)

    print("\n=== Module / escape-path candidates ===")
    if escape_hits:
        for hit in escape_hits[:25]:
            print(f"{hit['sid']}:")
            for line in hit["lines"]:
                print(f"  {line}")
        if len(escape_hits) > 25:
            print(f"... {len(escape_hits) - 25} more; see JSON report")
    else:
        print("No module/socket/attachment/fitting/preinstalled terms found.")

    if missing:
        print("\n=== Missing referenced upgrade SIDs ===")
        for sid in missing:
            print(sid)

    if args.details:
        print("\n=== Armor -> UpgradePrototypeSIDs ===")
        for armor in sorted(armors, key=lambda x: x["sid"]):
            print(f"\n{armor['sid']} ({len(armor['upgrades'])})")
            for upgrade in armor["upgrades"]:
                state = "OK" if upgrade in upgrade_structs else "MISSING"
                print(f"  [{state}] {upgrade}")

    print(f"\nReports written to: {REPORT_DIR}")
    for name in (
        "armor_upgrade_summary.json",
        "armor_upgrade_field_inventory.json",
        "armor_upgrade_escape_paths.json",
        "armor_upgrade_relations.json",
        "armor_upgrade_missing.json",
        "armor_upgrade_mapping.json",
        "armor_upgrade_details.json",
        "armor_modification_analysis.json",
        "armor_effect_analysis.json",
        "armor_effect_details.json",
    ):
        print(f"  - {name}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
