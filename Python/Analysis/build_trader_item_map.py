from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from analysis_paths import TRADER_ITEM_MAP, ensure_reports_dir

PYTHON_ROOT = Path(__file__).resolve().parents[1]
DYNAMIC_ITEM_GENERATOR = PYTHON_ROOT / "VanillaReference" / "DynamicItemGenerator.cfg"

STRUCT_BEGIN_RE = re.compile(r"^\s*([^:]+?)\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*$")
SID_RE = re.compile(r"^\s*SID\s*=\s*([^\s]+)\s*$")
CATEGORY_RE = re.compile(r"^\s*Category\s*=\s*EItemGenerationCategory::([^\s]+)\s*$")
ITEM_RE = re.compile(r"^\s*ItemPrototypeSID\s*=\s*([^\s]+)\s*$")
GENERATOR_RE = re.compile(r"^\s*ItemGeneratorPrototypeSID\s*=\s*([^\s]+)\s*$")
RANK_RE = re.compile(r"^\s*PlayerRank\s*=\s*(.+?)\s*$")
REPUTATION_RE = re.compile(r"^\s*ReputationThreshold\s*=\s*(.+?)\s*$")
REFRESH_RE = re.compile(r"^\s*RefreshTime\s*=\s*(.+?)\s*$")

WEAPON_CATEGORIES = {"WeaponPrimary", "WeaponSecondary", "WeaponPistol"}


def _strip_comment(line: str) -> str:
    return line.split("//", 1)[0].rstrip()


def _parse_rank(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip().removeprefix("ERank::") for part in value.split(",")]


def parse_generators(text: str) -> list[dict]:
    """Parse top-level item generators and their ItemGenerator category blocks."""
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


def build_report() -> dict:
    generators = parse_generators(DYNAMIC_ITEM_GENERATOR.read_text(encoding="utf-8-sig"))

    weapon_to_pools: dict[str, list[dict]] = defaultdict(list)
    attachment_to_pools: dict[str, list[dict]] = defaultdict(list)
    trader_pools: dict[str, dict] = {}

    for generator in generators:
        sid = generator["sid"]
        relevant_categories = [
            category
            for category in generator["categories"]
            if category["category"] in WEAPON_CATEGORIES or category["category"] == "Attach"
        ]
        if not relevant_categories:
            continue

        pool_data = {"weapon_pools": [], "attachment_pools": []}
        for index, category in enumerate(generator["categories"]):
            if category["category"] not in WEAPON_CATEGORIES and category["category"] != "Attach":
                continue

            entry = {
                "category_index": index,
                "category": category["category"],
                "player_ranks": category["player_ranks"],
                "reputation_threshold": category["reputation_threshold"],
                "refresh_time": category["refresh_time"],
                "items": category["items"],
                "nested_generators": category["nested_generators"],
            }
            target = "attachment_pools" if category["category"] == "Attach" else "weapon_pools"
            pool_data[target].append(entry)

            lookup_entry = {
                "generator_sid": sid,
                "category_index": index,
                "category": category["category"],
                "player_ranks": category["player_ranks"],
                "reputation_threshold": category["reputation_threshold"],
            }
            lookup = attachment_to_pools if category["category"] == "Attach" else weapon_to_pools
            for item_sid in category["items"]:
                lookup[item_sid].append(lookup_entry)

        trader_pools[sid] = pool_data

    return {
        "summary": {
            "generator_count": len(generators),
            "generator_count_with_weapons_or_attachments": len(trader_pools),
            "weapon_sid_count": len(weapon_to_pools),
            "attachment_sid_count": len(attachment_to_pools),
        },
        "weapon_to_pools": dict(sorted(weapon_to_pools.items())),
        "attachment_to_pools": dict(sorted(attachment_to_pools.items())),
        "trader_pools": dict(sorted(trader_pools.items())),
    }


def print_summary(report: dict) -> None:
    summary = report["summary"]
    print("Trader item generator audit")
    print("=" * 100)
    print(
        f"Generators={summary['generator_count']} | "
        f"weapon/attach generators={summary['generator_count_with_weapons_or_attachments']} | "
        f"weapons={summary['weapon_sid_count']} | "
        f"attachments={summary['attachment_sid_count']}"
    )
    print()
    print("Weapon -> generator pools")
    print("-" * 100)
    for weapon_sid, pools in report["weapon_to_pools"].items():
        pool_labels = []
        for pool in pools:
            ranks = ",".join(pool["player_ranks"]) or "any-rank"
            reputation = pool["reputation_threshold"] or "any-rep"
            pool_labels.append(
                f"{pool['generator_sid']}[{pool['category_index']}] "
                f"{pool['category']} rank={ranks} rep={reputation}"
            )
        print(f"{weapon_sid:<40} | {'; '.join(pool_labels)}")


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
