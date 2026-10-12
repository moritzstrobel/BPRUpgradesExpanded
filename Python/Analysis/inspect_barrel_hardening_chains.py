#!/usr/bin/env python3
"""Temporary read-only inspector for vanilla Barrel Hardening upgrade chains.

Run from mod Content:
 python Python/Analysis/inspect_barrel_hardening_chains.py Python/VanillaReference

Reads actual local CFGs, not GitHub's potentially empty reference placeholders.
Prints real prerequisite/blocking fields, effect SIDs and resolved effect types.
"""
import argparse
import re
from pathlib import Path

WEAPONS = {"SVD": "GunSVDM", "SVU": "GunSVU",
           "Three-Line": "GunThreeLine", "M701": "GunM701"}
BEGIN = re.compile(r"^\s*([\w]+)\s*:\s*struct\.begin\b")
NESTED = re.compile(r"^\s*(\w+)\s*:\s*struct\.begin\b")
END = re.compile(r"^\s*struct\.end\b")
VALUE = re.compile(r"^\s*(?:\[\d+\]|([\w]+))\s*=\s*([^/\r\n]+)")
IMPORTANT = ("RequiredUpgradePrototypeSIDs", "BlockedUpgradePrototypeSIDs",
             "BlockingUpgradePrototypeSIDs", "EffectPrototypeSIDs",
             "UpgradePrototypeSIDs", "PreinstalledUpgrades")


def parse_file(path):
    result = []
    stack = []
    name = None
    lines = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = BEGIN.match(line)
        if not stack:
            if match:
                name, lines, stack = match.group(1), [line], [name or ""]
        else:
            lines.append(line)
            if NESTED.match(line):
                stack.append(NESTED.match(line).group(1))
            elif END.match(line):
                stack.pop()
                if not stack:
                    result.append((name, "\n".join(lines)))
    return result


def fields(block):
    result = {}
    for line in block.splitlines():
        m = VALUE.match(line)
        if m and m.group(1):
            result[m.group(1)] = m.group(2).strip()
    return result


def nested_lists(block):
    """Read indexed entries from nested struct sections; do not confuse with setup."""
    result = {}
    stack = []
    for line in block.splitlines()[1:]:
        m = NESTED.match(line)
        if m:
            stack.append(m.group(1))
            continue
        if END.match(line):
            if stack:
                stack.pop()
            continue
        m = VALUE.match(line)
        if m and not m.group(1) and stack:
            result.setdefault(stack[-1], []).append(m.group(2).strip())
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", type=Path,
                    default=Path("Python/VanillaReference"))
    ap.add_argument("--all", action="store_true",
                    help="Also print all other upgrades for the four weapons")
    args = ap.parse_args()
    if not args.root.exists():
        ap.error(f"Directory does not exist: {args.root}")
    files = sorted(args.root.rglob("*.cfg"))
    definitions = {}
    for path in files:
        # Prefer canonical reference over OXA/DLC duplicate or bpatch variants.
        for sid, block in parse_file(path):
            definitions.setdefault(sid, []).append((path, block))
    print(f"Scanned {len(files)} CFGs; {len(definitions)} prototype SIDs")
    for weapon, prefix in WEAPONS.items():
        print(f"\n{'=' * 14} {weapon} {'=' * 14}")
        candidates = {sid: values for sid, values in definitions.items()
                      if sid.startswith(prefix + "_Upgrade_")
                      and (args.all or "_Barrel_" in sid)}
        for sid, values in sorted(candidates.items()):
            # Prefer actual UpgradePrototypes file over other prototype classes.
            matches = [(p, block) for p, block in values
                       if "UpgradePrototypes" in p.name]
            if not matches:
                continue
            # Prefer non-OXA and non-patch source.
            matches.sort(key=lambda x: ("OxaData" in str(x[0]),
                                        "patch" in x[0].name, len(str(x[0]))))
            path, block = matches[0]
            f = fields(block)
            lists = nested_lists(block)
            print(f"\n{sid}")
            print(f"  Source: {path}")
            for key in ("Text", "Hint", "HorizontalPosition",
                        "VerticalPosition", "UpgradeTargetPart"):
                if key in f:
                    print(f"  {key}: {f[key]}")
            for key, vals in lists.items():
                if any(word in key.lower() for word in
                       ("requir", "block", "exclus", "effect", "depend")):
                    print(f"  {key}: {', '.join(vals) or '(empty)'}")
                    if "Effect" in key:
                        for effect in vals:
                            ev = definitions.get(effect, [])
                            if ev:
                                ef = fields(ev[0][1])
                                print(f"    -> {effect}: Type={ef.get('Type', '?')}, "
                                      f"Value={ef.get('ValueMin', '?')}..{ef.get('ValueMax', '?')}")
                            else:
                                print(f"    -> {effect}: definition not in scanned CFGs")
            if not any("effect" in k.lower() for k in lists):
                print("  Effects: none explicitly defined")
            # Explicitly show whether any OTHER upgrade requires this one.
            successors = []
            for other, other_values in definitions.items():
                if other == sid or not other.startswith(prefix + "_Upgrade_"):
                    continue
                for op, ob in other_values:
                    if "UpgradePrototypes" not in op.name:
                        continue
                    ol = nested_lists(ob)
                    if any(sid in vals for k, vals in ol.items()
                           if "requir" in k.lower() or "depend" in k.lower()):
                        successors.append(other)
                        break
            print("  Direct successors: " + (", ".join(sorted(set(successors))) or "none"))
        print("\n  Note: Identify Barrel Hardening from Text/Hint or effects,")
        print("  then check whether it has successors. Names are localization SIDs.")
    print("\nThis is a source-level inspection; verify engine behavior in game.")


if __name__ == "__main__":
    main()
