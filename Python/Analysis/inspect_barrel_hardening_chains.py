#!/usr/bin/env python3
"""Temporary diagnostic: inspect vanilla barrel-upgrade chains (no file writes).

Run:
 python Python/Analysis/inspect_barrel_hardening_chains.py PATH/TO/UNPACKED/CFG
Optionally add --all to show every barrel-related node.
Provide the extracted ZoneKit GameLite directory, NOT the empty reference
Python/VanillaReference/UpgradePrototypes.cfg in this repository.
"""
import argparse
import re
from pathlib import Path

WEAPONS = {
    "SVD": ("GunSVDM",),
    "SVU": ("GunSVU",),
    "Three-Line": ("GunThreeLine",),
    "M701": ("GunM701",),
}
BEGIN = re.compile(r"^\s*([\w]+)\s*:\s*struct\.begin\b")
END = re.compile(r"^\s*struct\.end\b")
FIELD = re.compile(r"^\s*([\w]+)\s*=\s*(.*?)\s*(?://.*)?$")
LINK = re.compile(r"(?:depend|requir|block|exclus|previous|next|parent|prerequis|upgrade)", re.I)


def parse(path):
    # A top-level prototype may contain many nested struct.begin/end blocks.
    result = []
    depth = 0
    name = None
    body = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        start = BEGIN.match(line)
        if depth == 0 and start:
            name, body = start.group(1), [line]
            depth = 1
        elif depth:
            body.append(line)
            if start:
                depth += 1
            elif END.match(line):
                depth -= 1
                if depth == 0:
                    result.append((name, "\n".join(body)))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", type=Path, help="Extracted vanilla CFG folder")
    ap.add_argument("--all", action="store_true", help="Print every barrel prototype")
    args = ap.parse_args()
    if not args.root.exists():
        ap.error("CFG root not found")
    files = list(args.root.rglob("*.cfg"))
    if not files:
        ap.error("No .cfg files found (extract the ZoneKit vanilla data first)")
    definitions = {}
    refs = {}
    for path in files:
        for sid, block in parse(path):
            definitions.setdefault(sid, []).append((path, block))
            if "UpgradePrototypeSIDs" in block:
                refs.setdefault(sid, []).append((path, block))
    print(f"Scanned {len(files)} CFGs, {len(definitions)} prototype SIDs")
    for weapon, prefixes in WEAPONS.items():
        print(f"\n{'=' * 20} {weapon} {'=' * 20}")
        relevant = {sid for sid in definitions if sid.startswith(prefixes)
                    and "_Upgrade_" in sid and (args.all or "_Barrel_" in sid)}
        # Also show the list of upgrades in each weapon's actual setup.
        setups = [(sid, path, block) for sid, values in refs.items()
                  if sid.startswith(prefixes) for path, block in values
                  if "UpgradePrototypeSIDs" in block]
        for sid, path, block in setups:
            lines = block.splitlines()
            inside = False
            print(f"  SETUP {sid} [{path}]")
            for line in lines:
                if "UpgradePrototypeSIDs" in line:
                    inside = True
                elif inside and line.strip() == "struct.end":
                    inside = False
                elif inside and "_Upgrade_" in line:
                    print("   ", line.strip())
        if not relevant:
            print("  NO MATCHING BARREL PROTOTYPES (check dump paths/names)")
        for sid in sorted(relevant):
            for path, block in definitions[sid]:
                print(f"\n  {sid} [{path}]")
                for line in block.splitlines():
                    m = FIELD.match(line)
                    if m and (LINK.search(m.group(1)) or m.group(1) in (
                            "SID", "Text", "Hint", "HorizontalPosition",
                            "VerticalPosition", "UpgradeTarget", "UpgradeTargetSID")):
                        print("   ", line.strip())
                    elif re.search(r"\b(?:GunSVDM|GunSVU|GunThreeLine|GunM701)_Upgrade_\w+", line) and not BEGIN.match(line):
                        print("   ", line.strip())
        # Reverse links: find references from other upgrades to barrel nodes.
        print("\n  REVERSE REFERENCES:")
        count = 0
        for target in sorted(relevant):
            for source, values in definitions.items():
                if source == target or "_Upgrade_" not in source:
                    continue
                for path, block in values:
                    if re.search(r"\b" + re.escape(target) + r"\b", block):
                        print(f"   {source} -> {target} [{path}]")
                        count += 1
        if not count:
            print("   none found (or vanilla dependency data missing)")
    print("\nNOTE: A position or numeric suffix alone does not prove dependency.")
    print("Inspect the reported fields, reverse links and weapon setup together.")


if __name__ == "__main__":
    main()
