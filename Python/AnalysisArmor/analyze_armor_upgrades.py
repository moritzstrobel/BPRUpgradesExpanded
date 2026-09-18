#!/usr/bin/env python3
"""Analyze Vanilla armor upgrade topology.

This intentionally stays read-only. It correlates ArmorPrototypes.cfg with
UpgradePrototypes.cfg and reports whether armor exposes module-like escape
paths in addition to the ordinary UpgradePrototypeSIDs tree.

The parser is deliberately lightweight: STALKER cfg is not quite a regular
INI format, so we scan balanced struct blocks and retain the original text.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VANILLA = ROOT / "VanillaReference"
ARMOR_CFG = VANILLA / "ArmorPrototypes.cfg"
UPGRADE_CFG = VANILLA / "UpgradePrototypes.cfg"

STRUCT_START = re.compile(r"^\s*([^/\s][^:]*)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?\s*$")
UPGRADE_SID = re.compile(r"^\s*\[\d+\]\s*=\s*([^\s{]+)", re.MULTILINE)
SID_FIELD = re.compile(r"^\s*SID\s*=\s*([^\s]+)", re.MULTILINE)

# Terms worth auditing because weapons use additional indirections/mechanics
# around their normal upgrade trees. This is discovery, not an assumption
# that armor uses the same fields.
ESCAPE_TERMS = (
    "module",
    "socket",
    "attachment",
    "fitting",
    "preinstalled",
    "effectprototypesid",
    "upgradeprototypesid",
)


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
            depth += len(re.findall(r"\bstruct\.begin\b", lines[j]))
            depth -= len(re.findall(r"\bstruct\.end\b", lines[j]))
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
            depth += len(re.findall(r"\bstruct\.begin\b", lines[j]))
            depth -= len(re.findall(r"\bstruct\.end\b", lines[j]))
            j += 1
        return "\n".join(lines[i:j])
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--armor", help="Only show armor SIDs containing this text")
    parser.add_argument("--details", action="store_true", help="Print every armor and its referenced upgrade SIDs")
    args = parser.parse_args()

    armor_text = ARMOR_CFG.read_text(encoding="utf-8")
    upgrade_text = UPGRADE_CFG.read_text(encoding="utf-8")
    armor_structs = top_level_structs(armor_text)
    upgrade_structs = top_level_structs(upgrade_text)

    armors: list[tuple[str, list[str], str]] = []
    referenced: set[str] = set()

    for name, block in armor_structs.items():
        sid_match = SID_FIELD.search(block)
        sid = sid_match.group(1) if sid_match else name
        if args.armor and args.armor.lower() not in sid.lower():
            continue
        upgrade_array = extract_named_struct(block, "UpgradePrototypeSIDs")
        upgrades = UPGRADE_SID.findall(upgrade_array or "")
        upgrades = [u for u in upgrades if u != "empty"]
        referenced.update(upgrades)
        armors.append((sid, upgrades, block))

    resolved = referenced.intersection(upgrade_structs)
    missing = referenced.difference(upgrade_structs)

    print("=== BPRUE Vanilla Armor Upgrade Analysis ===")
    print(f"Armor structs selected: {len(armors)}")
    print(f"Referenced upgrade SIDs: {len(referenced)}")
    print(f"Resolved in UpgradePrototypes.cfg: {len(resolved)}")
    print(f"Missing from UpgradePrototypes.cfg: {len(missing)}")

    print("\n=== Potential module / escape-path fields in ArmorPrototypes ===")
    counts = Counter()
    examples: dict[str, list[str]] = {term: [] for term in ESCAPE_TERMS}
    for sid, _, block in armors:
        low = block.lower()
        for term in ESCAPE_TERMS:
            if term in low:
                counts[term] += 1
                if len(examples[term]) < 5:
                    examples[term].append(sid)

    for term in ESCAPE_TERMS:
        if counts[term]:
            print(f"{term}: {counts[term]} armor structs; examples={', '.join(examples[term])}")

    # Search upgrade definitions referenced by armor for module-ish fields too.
    print("\n=== Potential module / escape-path fields in referenced UpgradePrototypes ===")
    upgrade_counts = Counter()
    upgrade_examples: dict[str, list[str]] = {term: [] for term in ESCAPE_TERMS}
    for sid in sorted(resolved):
        low = upgrade_structs[sid].lower()
        for term in ESCAPE_TERMS:
            if term in low:
                upgrade_counts[term] += 1
                if len(upgrade_examples[term]) < 5:
                    upgrade_examples[term].append(sid)

    found_escape = False
    for term in ESCAPE_TERMS:
        if upgrade_counts[term]:
            found_escape = True
            print(f"{term}: {upgrade_counts[term]} referenced upgrades; examples={', '.join(upgrade_examples[term])}")
    if not found_escape:
        print("No module-like terms found in referenced armor upgrade definitions.")

    if missing:
        print("\n=== Missing referenced upgrade SIDs ===")
        for sid in sorted(missing):
            print(sid)

    if args.details:
        print("\n=== Armor -> UpgradePrototypeSIDs ===")
        for sid, upgrades, _ in sorted(armors):
            print(f"\n{sid} ({len(upgrades)})")
            for upgrade in upgrades:
                state = "OK" if upgrade in upgrade_structs else "MISSING"
                print(f"  [{state}] {upgrade}")

    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
