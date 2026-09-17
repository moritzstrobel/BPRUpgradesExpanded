from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from analysis_paths import TRADER_ITEM_MAP, ensure_reports_dir

PYTHON_ROOT = Path(__file__).resolve().parents[1]
DYNAMIC_ITEM_GENERATOR = PYTHON_ROOT / "VanillaReference" / "DynamicItemGenerator.cfg"
ITEM_GENERATOR_PROTOTYPES = PYTHON_ROOT / "VanillaReference" / "ItemGeneratorPrototypes.cfg"

STRUCT_BEGIN_RE = re.compile(r"^\s*([^:]+?)\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*$")
SID_RE = re.compile(r"^\s*SID\s*=\s*([^\s]+)\s*$")
CATEGORY_RE = re.compile(r"^\s*Category\s*=\s*EItemGenerationCategory::([^\s]+)\s*$")
ITEM_RE = re.compile(r"^\s*ItemPrototypeSID\s*=\s*([^\s]+)\s*$")
GENERATOR_RE = re.compile(r"^\s*ItemGeneratorPrototypeSID\s*=\s*([^\s]+)\s*$")
RANK_RE = re.compile(r"^\s*PlayerRank\s*=\s*(.+?)\s*$")
REPUTATION_RE = re.compile(r"^\s*ReputationThreshold\s*=\s*(.+?)\s*$")
REFRESH_RE = re.compile(r"^\s*RefreshTime\s*=\s*(.+?)\s*$")
TRADER_GUN_TIER_RE = re.compile(r"^Trader_T(\d+)_Guns_ItemGenerator$")
TRADER_ATTACHMENT_TIER_RE = re.compile(r"^Trader_Attachments_T(\d+)_ItemGenerator$")

WEAPON_CATEGORIES = {"WeaponPrimary", "WeaponSecondary", "WeaponPistol"}
TRADER_POOL_PREFIX = "Trader_"
CONVERSION_WEAPONS = (
    "GunViper_PP",
    "GunAKU_PP",
    "GunBucket_PP",
    "GunIntegral_PP",
    "GunZubr_PP",
    "GunFora230_PP",
)


def _strip_comment(line: str) -> str:
    return line.split("//", 1)[0].rstrip()


def _parse_rank(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().removeprefix("ERank::") for part in value.split(",")]


def parse_generators(text: str, source: str) -> list[dict]:
    """Parse all top-level item generators and their category blocks."""
    generators: list[dict] = []
    stack: list[dict] = []
    current_generator: dict | None = None
    current_category: dict | None = None

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line)
        if not line.strip():
            continue

        begin = STRUCT_BEGIN_RE.match(line)
        if begin:
            node = {"key": begin.group(1).strip()}
            stack.append(node)
            if len(stack) == 1:
                current_generator = {
                    "struct_key": node["key"],
                    "sid": None,
                    "source": source,
                    "categories": [],
                }
                generators.append(current_generator)
            continue

        if line.strip() == "struct.end":
            if current_category is not None and len(stack) == current_category["_depth"]:
                current_category.pop("_depth", None)
                current_category = None
            if len(stack) == 1:
                current_generator = None
            if stack:
                stack.pop()
            continue

        if current_generator is None:
            continue

        sid = SID_RE.match(line)
        if sid and len(stack) == 1:
            current_generator["sid"] = sid.group(1)
            continue

        category = CATEGORY_RE.match(line)
        if category:
            current_category = {
                "category": category.group(1),
                "player_ranks": [],
                "reputation_threshold": None,
                "refresh_time": None,
                "items": [],
                "nested_generators": [],
                "_depth": len(stack),
            }
            current_generator["categories"].append(current_category)
            continue

        if current_category is None:
            continue

        rank = RANK_RE.match(line)
        if rank:
            current_category["player_ranks"] = _parse_rank(rank.group(1))
            continue
        reputation = REPUTATION_RE.match(line)
        if reputation:
            current_category["reputation_threshold"] = reputation.group(1)
            continue
        refresh = REFRESH_RE.match(line)
        if refresh:
            current_category["refresh_time"] = refresh.group(1)
            continue
        item = ITEM_RE.match(line)
        if item:
            item_sid = item.group(1)
            if item_sid != "empty":
                current_category["items"].append(item_sid)
            continue
        nested = GENERATOR_RE.match(line)
        if nested:
            generator_sid = nested.group(1)
            if generator_sid != "empty":
                current_category["nested_generators"].append(generator_sid)

    for generator in generators:
        generator["sid"] = generator["sid"] or generator["struct_key"]
    return generators


def _category_context(generator: dict, category_index: int, category: dict) -> dict:
    return {
        "generator_sid": generator["sid"],
        "source": generator["source"],
        "category_index": category_index,
        "category": category["category"],
        "player_ranks": category["player_ranks"],
        "reputation_threshold": category["reputation_threshold"],
        "refresh_time": category["refresh_time"],
    }


def _walk_generator(
    generator_sid: str,
    definitions: dict[str, dict],
    path: tuple[str, ...],
    unresolved: set[str],
) -> list[dict]:
    """Resolve ItemGeneratorPrototypeSID recursively and retain the complete path."""
    if generator_sid in path:
        return [{"type": "cycle", "generator_sid": generator_sid, "path": list(path + (generator_sid,))}]

    generator = definitions.get(generator_sid)
    if generator is None:
        unresolved.add(generator_sid)
        return [{"type": "unresolved_generator", "generator_sid": generator_sid, "path": list(path)}]

    current_path = path + (generator_sid,)
    resolved: list[dict] = []
    for category_index, category in enumerate(generator["categories"]):
        context = _category_context(generator, category_index, category)
        for item_sid in category["items"]:
            resolved.append({
                "type": "item",
                "item_sid": item_sid,
                "path": list(current_path),
                **context,
            })
        for nested_sid in category["nested_generators"]:
            resolved.extend(_walk_generator(nested_sid, definitions, current_path, unresolved))
    return resolved


def _tier_from_paths(details: list[dict], pattern: re.Pattern[str]) -> list[dict]:
    """Return all tiered generators found in resolved paths, sorted by tier."""
    found: dict[tuple[int, str], dict] = {}
    for detail in details:
        for generator_sid in detail["path"]:
            match = pattern.match(generator_sid)
            if match:
                tier = int(match.group(1))
                found[(tier, generator_sid)] = {
                    "tier": tier,
                    "generator_sid": generator_sid,
                }
    return [found[key] for key in sorted(found)]


def _build_conversion_weapon_analysis(
    weapon_to_traders: dict[str, list[dict]],
    traders: dict[str, dict],
) -> dict[str, dict]:
    analysis: dict[str, dict] = {}

    for weapon_sid in CONVERSION_WEAPONS:
        trader_entries = weapon_to_traders.get(weapon_sid, [])
        gun_pools: dict[tuple[int, str], dict] = {}
        trader_details: list[dict] = []

        for trader_entry in trader_entries:
            trader_sid = trader_entry["trader_sid"]
            source_details = trader_entry["sources"]
            source_gun_pools = _tier_from_paths(source_details, TRADER_GUN_TIER_RE)
            for pool in source_gun_pools:
                gun_pools[(pool["tier"], pool["generator_sid"])] = pool

            direct_attachment_pools = []
            for pool_sid in traders[trader_sid]["direct_trader_pool_refs"]:
                match = TRADER_ATTACHMENT_TIER_RE.match(pool_sid)
                if match:
                    direct_attachment_pools.append({
                        "tier": int(match.group(1)),
                        "generator_sid": pool_sid,
                    })

            trader_details.append({
                "trader_sid": trader_sid,
                "weapon_gun_pools": source_gun_pools,
                "direct_attachment_pools": sorted(
                    direct_attachment_pools,
                    key=lambda pool: (pool["tier"], pool["generator_sid"]),
                ),
            })

        sorted_gun_pools = [gun_pools[key] for key in sorted(gun_pools)]
        earliest_tier = min((pool["tier"] for pool in sorted_gun_pools), default=None)
        suggested_attachment_pool = (
            f"Trader_Attachments_T{earliest_tier}_ItemGenerator"
            if earliest_tier is not None
            else None
        )

        analysis[weapon_sid] = {
            "earliest_gun_tier": earliest_tier,
            "gun_pools": sorted_gun_pools,
            "suggested_attachment_pool": suggested_attachment_pool,
            "traders": trader_details,
        }

    return analysis


def build_report() -> dict:
    dynamic_generators = parse_generators(
        DYNAMIC_ITEM_GENERATOR.read_text(encoding="utf-8-sig"),
        "DynamicItemGenerator.cfg",
    )
    prototype_generators = parse_generators(
        ITEM_GENERATOR_PROTOTYPES.read_text(encoding="utf-8-sig"),
        "ItemGeneratorPrototypes.cfg",
    )

    # DynamicItemGenerator is the more specific definition space and therefore wins on SID collisions.
    definitions = {generator["sid"]: generator for generator in prototype_generators}
    definitions.update({generator["sid"]: generator for generator in dynamic_generators})

    # Discover trader roots structurally. Their own names are deliberately irrelevant.
    trader_roots: list[dict] = []
    for generator in dynamic_generators:
        direct_refs = {
            nested_sid
            for category in generator["categories"]
            for nested_sid in category["nested_generators"]
        }
        trader_pool_refs = sorted(ref for ref in direct_refs if ref.startswith(TRADER_POOL_PREFIX))
        if trader_pool_refs:
            trader_roots.append({
                "sid": generator["sid"],
                "source": generator["source"],
                "direct_trader_pool_refs": trader_pool_refs,
            })

    unresolved: set[str] = set()
    traders: dict[str, dict] = {}
    weapon_to_traders: dict[str, list[dict]] = defaultdict(list)
    attachment_to_traders: dict[str, list[dict]] = defaultdict(list)

    for root in trader_roots:
        resolved = _walk_generator(root["sid"], definitions, (), unresolved)
        weapons: dict[str, list[dict]] = defaultdict(list)
        attachments: dict[str, list[dict]] = defaultdict(list)
        other_items: dict[str, list[dict]] = defaultdict(list)
        cycles: list[dict] = []
        unresolved_for_root: list[dict] = []

        for entry in resolved:
            if entry["type"] == "cycle":
                cycles.append(entry)
                continue
            if entry["type"] == "unresolved_generator":
                unresolved_for_root.append(entry)
                continue

            detail = {
                "via_generator": entry["generator_sid"],
                "source": entry["source"],
                "category_index": entry["category_index"],
                "category": entry["category"],
                "player_ranks": entry["player_ranks"],
                "reputation_threshold": entry["reputation_threshold"],
                "refresh_time": entry["refresh_time"],
                "path": entry["path"],
            }
            item_sid = entry["item_sid"]
            if entry["category"] in WEAPON_CATEGORIES:
                weapons[item_sid].append(detail)
            elif entry["category"] == "Attach":
                attachments[item_sid].append(detail)
            else:
                other_items[item_sid].append(detail)

        traders[root["sid"]] = {
            "direct_trader_pool_refs": root["direct_trader_pool_refs"],
            "weapons": dict(sorted(weapons.items())),
            "attachments": dict(sorted(attachments.items())),
            "other_items": dict(sorted(other_items.items())),
            "cycles": cycles,
            "unresolved_generators": unresolved_for_root,
        }

        for weapon_sid, details in weapons.items():
            weapon_to_traders[weapon_sid].append({
                "trader_sid": root["sid"],
                "sources": details,
            })
        for attachment_sid, details in attachments.items():
            attachment_to_traders[attachment_sid].append({
                "trader_sid": root["sid"],
                "sources": details,
            })

    conversion_weapon_analysis = _build_conversion_weapon_analysis(
        weapon_to_traders,
        traders,
    )

    return {
        "summary": {
            "dynamic_generator_count": len(dynamic_generators),
            "prototype_generator_count": len(prototype_generators),
            "definition_count": len(definitions),
            "trader_root_count": len(trader_roots),
            "weapon_sid_count": len(weapon_to_traders),
            "attachment_sid_count": len(attachment_to_traders),
            "unresolved_generator_count": len(unresolved),
        },
        "trader_roots": [root["sid"] for root in trader_roots],
        "weapon_to_traders": dict(sorted(weapon_to_traders.items())),
        "attachment_to_traders": dict(sorted(attachment_to_traders.items())),
        "conversion_weapon_analysis": conversion_weapon_analysis,
        "traders": dict(sorted(traders.items())),
        "unresolved_generators": sorted(unresolved),
    }


def print_summary(report: dict) -> None:
    summary = report["summary"]
    print("Trader item generator graph audit")
    print("=" * 100)
    print(
        f"Dynamic generators={summary['dynamic_generator_count']} | "
        f"prototype generators={summary['prototype_generator_count']} | "
        f"definitions={summary['definition_count']} | "
        f"trader roots={summary['trader_root_count']} | "
        f"weapons={summary['weapon_sid_count']} | "
        f"attachments={summary['attachment_sid_count']} | "
        f"unresolved={summary['unresolved_generator_count']}"
    )
    print()
    print("Trader roots")
    print("-" * 100)
    for trader_sid in report["trader_roots"]:
        trader = report["traders"][trader_sid]
        print(
            f"{trader_sid:<50} | "
            f"weapons={len(trader['weapons']):>3} | "
            f"attachments={len(trader['attachments']):>3} | "
            f"pools={', '.join(trader['direct_trader_pool_refs'])}"
        )

    print()
    print("Conversion kit tier analysis")
    print("-" * 100)
    print(f"{'Weapon':<30} | {'Earliest gun pool':<34} | Suggested attachment pool")
    print("-" * 100)
    for weapon_sid in CONVERSION_WEAPONS:
        entry = report["conversion_weapon_analysis"][weapon_sid]
        earliest_pool = (
            f"Trader_T{entry['earliest_gun_tier']}_Guns_ItemGenerator"
            if entry["earliest_gun_tier"] is not None
            else "(not found)"
        )
        suggested = entry["suggested_attachment_pool"] or "(not found)"
        print(f"{weapon_sid:<30} | {earliest_pool:<34} | {suggested}")

    if report["unresolved_generators"]:
        print()
        print("Unresolved generator references")
        print("-" * 100)
        for sid in report["unresolved_generators"]:
            print(sid)


def main() -> None:
    report = build_report()
    ensure_reports_dir()
    TRADER_ITEM_MAP.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print_summary(report)
    print(f"\nReport: {TRADER_ITEM_MAP}")


if __name__ == "__main__":
    main()
