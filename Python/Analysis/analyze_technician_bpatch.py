#!/usr/bin/env python3
"""Simulate STALKER 2 {bpatch} for NPC technician Upgrades and analyse the result.

Purpose:
- Load the Vanilla NPCPrototypes.cfg.
- Load BPRUE's generated NPCPrototypes patch.
- Apply only the subset of official bpatch semantics used by BPRUE:
  * "Root : struct.begin {bpatch}" patches an existing root.
  * "Upgrades : struct.begin {bpatch}" preserves existing children.
  * "[*] : struct.begin" appends a new child.
- Resolve refkey inheritance for technicians after patching.
- Report whether Vanilla upgrade entries were lost/changed and whether BPRUE
  creates duplicate upgrade SIDs or changes inherited technician behaviour.

This is intentionally a diagnostic simulator, not a general CFG parser.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VANILLA = ROOT / "Python/VanillaReference/NPCPrototypes.cfg"
DEFAULT_PATCH = ROOT / "Content/GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"

ROOT_RE = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?\s*$"
)
REFKEY_RE = re.compile(r"\brefkey\s*=\s*([^;}\s]+)")
UPGRADE_SID_RE = re.compile(r"^\s*UpgradePrototypeSID\s*=\s*([^\s/]+)")
NPC_TYPE_RE = re.compile(r"^\s*NPCType\s*=\s*ENPCType::([^\s/]+)")


@dataclass
class Prototype:
    sid: str
    header: str
    refkey: str | None
    npc_type: str | None
    direct_upgrades: list[str] | None
    patch_upgrades: list[str] = field(default_factory=list)


def extract_struct(lines: list[str], start: int) -> tuple[list[str], int]:
    block: list[str] = []
    depth = 0
    i = start
    while i < len(lines):
        line = lines[i]
        block.append(line)
        if "struct.begin" in line:
            depth += line.count("struct.begin")
        if "struct.end" in line:
            depth -= line.count("struct.end")
            if depth == 0:
                return block, i + 1
        i += 1
    raise ValueError(f"Unclosed struct beginning at line {start + 1}")


def direct_child(block: list[str], name: str) -> list[str] | None:
    needle = re.compile(rf"^\s*{re.escape(name)}\s*:\s*struct\.begin")
    depth = 0
    for i, line in enumerate(block):
        if i == 0:
            depth = 1
            continue
        if depth == 1 and needle.match(line):
            child, _ = extract_struct(block, i)
            return child
        depth += line.count("struct.begin")
        depth -= line.count("struct.end")
    return None


def parse_upgrade_sids(upgrades: list[str] | None) -> list[str]:
    if not upgrades:
        return []
    result: list[str] = []
    for line in upgrades:
        m = UPGRADE_SID_RE.match(line)
        if m:
            result.append(m.group(1))
    return result


def parse_file(path: Path) -> dict[str, Prototype]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    result: dict[str, Prototype] = {}
    i = 0
    while i < len(lines):
        m = ROOT_RE.match(lines[i])
        if not m:
            i += 1
            continue
        block, next_i = extract_struct(lines, i)
        sid = m.group(1)
        ref_m = REFKEY_RE.search(lines[i])
        refkey = ref_m.group(1) if ref_m else None
        npc_type = None
        depth = 0
        for j, line in enumerate(block):
            if j == 0:
                depth = 1
                continue
            if depth == 1:
                n = NPC_TYPE_RE.match(line)
                if n:
                    npc_type = n.group(1)
            depth += line.count("struct.begin")
            depth -= line.count("struct.end")
        upgrades = direct_child(block, "Upgrades")
        result[sid] = Prototype(
            sid=sid,
            header=lines[i],
            refkey=refkey,
            npc_type=npc_type,
            direct_upgrades=parse_upgrade_sids(upgrades) if upgrades is not None else None,
        )
        i = next_i
    return result


def effective_value(protos: dict[str, Prototype], sid: str, attr: str):
    seen: set[str] = set()
    current = sid
    while current and current not in seen:
        seen.add(current)
        p = protos.get(current)
        if not p:
            return None
        value = getattr(p, attr)
        if value is not None:
            return value
        current = p.refkey
    return None


def effective_upgrades(protos: dict[str, Prototype], sid: str) -> list[str]:
    value = effective_value(protos, sid, "direct_upgrades")
    return list(value or [])


def is_technician(protos: dict[str, Prototype], sid: str) -> bool:
    return effective_value(protos, sid, "npc_type") == "Technician"


def apply_bprue_patch(
    vanilla: dict[str, Prototype], patch: dict[str, Prototype]
) -> tuple[dict[str, Prototype], list[str]]:
    # Clone the tiny model so comparison remains possible.
    merged = {
        sid: Prototype(
            sid=p.sid,
            header=p.header,
            refkey=p.refkey,
            npc_type=p.npc_type,
            direct_upgrades=None if p.direct_upgrades is None else list(p.direct_upgrades),
        )
        for sid, p in vanilla.items()
    }
    warnings: list[str] = []

    for sid, pp in patch.items():
        root_is_bpatch = "{bpatch}" in pp.header.replace(" ", "")
        if not root_is_bpatch:
            warnings.append(f"{sid}: patch root is not {{bpatch}}; simulator refuses replacement semantics")
            continue
        if sid not in merged:
            warnings.append(f"{sid}: {{bpatch}} targets missing Vanilla root")
            continue

        # BPRUE's renderer only patches Upgrades. The official semantics preserve
        # all other root children. For Upgrades {bpatch}, [*] children append.
        if pp.direct_upgrades is None:
            continue

        target = merged[sid]
        inherited_before = target.direct_upgrades is None
        if target.direct_upgrades is None:
            # Important semantic diagnostic: adding a direct Upgrades child to a
            # prototype that previously inherited it shadows the inherited child.
            inherited = effective_upgrades(merged, sid)
            target.direct_upgrades = list(inherited)
            warnings.append(
                f"{sid}: patch materializes inherited Upgrades "
                f"({len(inherited)} inherited entries) before appending"
            )

        target.direct_upgrades.extend(pp.direct_upgrades)
        target.patch_upgrades.extend(pp.direct_upgrades)

        if inherited_before and target.refkey:
            warnings.append(
                f"{sid}: now owns an Upgrades node although Vanilla inherited it from {target.refkey}"
            )

    return merged, warnings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanilla", type=Path, default=DEFAULT_VANILLA)
    ap.add_argument("--patch", type=Path, default=DEFAULT_PATCH)
    ap.add_argument("--technician", action="append", default=[],
                    help="Limit detailed output to one or more technician SIDs.")
    args = ap.parse_args()

    vanilla = parse_file(args.vanilla)
    patch = parse_file(args.patch)
    merged, warnings = apply_bprue_patch(vanilla, patch)

    technicians = sorted(sid for sid in vanilla if is_technician(vanilla, sid))
    patched_technicians = sorted(sid for sid in patch if sid in vanilla and is_technician(vanilla, sid))

    print("=== BPRUE Technician bpatch simulation ===")
    print(f"Vanilla roots       : {len(vanilla)}")
    print(f"Patch roots         : {len(patch)}")
    print(f"Vanilla technicians : {len(technicians)}")
    print(f"Patched technicians : {len(patched_technicians)}")
    print()

    lost_total = changed_order_total = duplicate_total = 0
    interesting: list[tuple[str, int, int, int, int, bool]] = []

    for sid in technicians:
        before = effective_upgrades(vanilla, sid)
        after = effective_upgrades(merged, sid)
        before_set = set(before)
        after_set = set(after)
        lost = [x for x in before if x not in after_set]
        vanilla_after = [x for x in after if x in before_set]
        order_changed = vanilla_after != before
        duplicates = [x for x, n in Counter(after).items() if n > 1]
        added = [x for x in after if x not in before_set]

        lost_total += len(lost)
        changed_order_total += int(order_changed)
        duplicate_total += len(duplicates)

        if lost or order_changed or duplicates or added or sid in args.technician:
            interesting.append(
                (sid, len(before), len(after), len(added), len(duplicates), order_changed)
            )

        if lost:
            print(f"ERROR {sid}: LOST {len(lost)} Vanilla upgrades")
            for x in lost[:20]:
                print(f"  - {x}")
            if len(lost) > 20:
                print(f"  ... {len(lost) - 20} more")

    print("=== Integrity summary ===")
    print(f"Lost Vanilla upgrade entries       : {lost_total}")
    print(f"Technicians with Vanilla reordering: {changed_order_total}")
    print(f"Duplicate effective upgrade SIDs    : {duplicate_total}")
    print()

    print("=== Patched/effected technicians ===")
    wanted = set(args.technician)
    for sid, before_n, after_n, added_n, dup_n, reordered in interesting:
        if wanted and sid not in wanted:
            continue
        own_before = vanilla[sid].direct_upgrades is not None
        own_after = merged[sid].direct_upgrades is not None
        print(
            f"{sid}: vanilla={before_n}, merged={after_n}, added={added_n}, "
            f"duplicates={dup_n}, reordered={reordered}, "
            f"ownUpgrades={own_before}->{own_after}, refkey={vanilla[sid].refkey}"
        )

    if warnings:
        print()
        print("=== Structural warnings ===")
        for warning in warnings:
            print(f"WARN {warning}")

    print()
    if lost_total or changed_order_total:
        print("RESULT: simulated patch changes Vanilla technician upgrade data.")
        return 2
    print("RESULT: no Vanilla upgrade SID was lost or reordered by the simulated bpatch.")
    if duplicate_total:
        print("NOTE: duplicate effective SIDs exist and should be inspected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
