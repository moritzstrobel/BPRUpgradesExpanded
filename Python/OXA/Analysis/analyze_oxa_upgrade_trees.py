from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Python" / "Analysis"))

from analyze_oxa_conflicts import (  # noqa: E402
    Write,
    _apply_array_patch,
    _entry_identity,
    _semantic_arrays,
    _writes_by_semantic_group,
    collect,
    collect_vanilla,
)

DEFAULT_OXA_ROOT = ROOT / "Python/VanillaReference/OxaData"
DEFAULT_VANILLA_ROOT = ROOT / "Python/VanillaReference"
DEFAULT_INVENTORY = ROOT / "Python/OXA/Reports/oxa_weapons.json"
DEFAULT_TEXT_OUT = ROOT / "Python/OXA/Reports/oxa_upgrade_trees.txt"
DEFAULT_JSON_OUT = ROOT / "Python/OXA/Reports/oxa_upgrade_trees.json"

GRAPH_ARRAYS = {
    "UpgradePrototypeSIDs",
    "RequiredUpgradeIDs",
    "InterchangeableUpgradePrototypeSIDs",
    "EffectPrototypeSIDs",
    "CompatibleAttachments",
}


def _by_prototype(writes: list[Write]) -> dict[str, list[Write]]:
    result: dict[str, list[Write]] = defaultdict(list)
    for write in writes:
        result[write.prototype].append(write)
    return result


def _effective_array(vanilla: list[Write], oxa: list[Write], sid: str, root: str) -> list[dict]:
    vanilla_group = _semantic_arrays(vanilla).get((sid, root), {"entries": {}})
    base = {idx: dict(fields) for idx, fields in vanilla_group["entries"].items()}
    group_writes = _writes_by_semantic_group(oxa).get((sid, root), [])
    if group_writes:
        state, _ = _apply_array_patch(base, group_writes, root)
    else:
        state = base
    result = []
    for index in sorted(
        state,
        key=lambda x: int(x[1:-1]) if x.startswith("[") and x[1:-1].isdigit() else 10**9,
    ):
        fields = state[index]
        identity = _entry_identity(root, fields)
        if identity:
            result.append({"index": index, "sid": identity, "fields": fields})
    return result


def _scalar_values(writes: list[Write], sid: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for w in writes:
        if w.prototype == sid and w.kind == "scalar":
            top = w.path.split(".", 1)[0]
            if top not in GRAPH_ARRAYS:
                result[w.path].append(w.value or "")
    return dict(result)


def analyze_weapon(
    vanilla: list[Write],
    oxa: list[Write],
    vanilla_by_proto: dict[str, list[Write]],
    oxa_by_proto: dict[str, list[Write]],
    weapon_sid: str,
) -> dict:
    weapon_writes = oxa_by_proto.get(weapon_sid, [])
    upgrades = _effective_array(vanilla, oxa, weapon_sid, "UpgradePrototypeSIDs")
    attachments = _effective_array(vanilla, oxa, weapon_sid, "CompatibleAttachments")

    queue = deque(x["sid"] for x in upgrades)
    seen = set()
    upgrade_nodes = []

    while queue:
        sid = queue.popleft()
        if sid in seen:
            continue
        seen.add(sid)
        vanilla_writes = vanilla_by_proto.get(sid, [])
        oxa_writes = oxa_by_proto.get(sid, [])
        writes = vanilla_writes + oxa_writes
        required = _effective_array(vanilla, oxa, sid, "RequiredUpgradeIDs")
        interchangeable = _effective_array(vanilla, oxa, sid, "InterchangeableUpgradePrototypeSIDs")
        effects = _effective_array(vanilla, oxa, sid, "EffectPrototypeSIDs")
        upgrade_nodes.append({
            "sid": sid,
            "defined": bool(writes),
            "sources": sorted({w.source for w in writes}),
            "definition_origin": (
                "VANILLA_AND_OXA" if vanilla_writes and oxa_writes
                else "OXA" if oxa_writes
                else "VANILLA" if vanilla_writes
                else "MISSING"
            ),
            "required": [x["sid"] for x in required],
            "interchangeable": [x["sid"] for x in interchangeable],
            "effects": [x["sid"] for x in effects],
            "scalars": _scalar_values(writes, sid),
        })
        for edge in required + interchangeable:
            if edge["sid"] not in seen:
                queue.append(edge["sid"])

    return {
        "weapon_sid": weapon_sid,
        "sources": sorted({w.source for w in weapon_writes}),
        "upgrade_roots": [x["sid"] for x in upgrades],
        "attachments": attachments,
        "upgrade_nodes": upgrade_nodes,
        "missing_upgrade_prototypes": sorted(x["sid"] for x in upgrade_nodes if not x["defined"]),
    }


def render(result: dict) -> str:
    lines = [
        "OXA new-SID upgrade trees",
        "=========================",
        f"Weapons: {len(result['weapons'])}",
        "",
    ]
    for weapon in result["weapons"]:
        lines += [
            weapon["weapon_sid"],
            "-" * len(weapon["weapon_sid"]),
            f"Upgrade roots: {len(weapon['upgrade_roots'])}",
            f"Reachable upgrade nodes: {len(weapon['upgrade_nodes'])}",
            f"Compatible attachments: {len(weapon['attachments'])}",
            f"Missing upgrade prototypes: {len(weapon['missing_upgrade_prototypes'])}",
        ]
        for sid in weapon["upgrade_roots"]:
            lines.append(f"  root: {sid}")
        for node in weapon["upgrade_nodes"]:
            req = ", ".join(node["required"]) or "-"
            inter = ", ".join(node["interchangeable"]) or "-"
            effects = ", ".join(node["effects"]) or "-"
            marker = "" if node["defined"] else " [MISSING]"
            lines.append(f"  {node['sid']}{marker} [{node['definition_origin']}]")
            lines.append(f"    required: {req}")
            lines.append(f"    interchangeable: {inter}")
            lines.append(f"    effects: {effects}")
        if weapon["missing_upgrade_prototypes"]:
            lines.append("  unresolved: " + ", ".join(weapon["missing_upgrade_prototypes"]))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Reconstruct OXA upgrade graphs for OXA-new weapon SIDs.")
    parser.add_argument("--oxa-root", type=Path, default=DEFAULT_OXA_ROOT)
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--weapon", action="append", default=[], help="Analyze only this SID; repeatable.")
    parser.add_argument("--text-out", type=Path, default=DEFAULT_TEXT_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args()

    oxa = collect(args.oxa_root)
    vanilla = collect_vanilla(args.vanilla_root)
    oxa_by_proto = _by_prototype(oxa)
    vanilla_by_proto = _by_prototype(vanilla)

    if args.weapon:
        weapon_sids = args.weapon
    else:
        inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
        weapon_sids = [x["sid"] for x in inventory.get("oxa_new_sid", [])]

    result = {
        "weapons": [
            analyze_weapon(vanilla, oxa, vanilla_by_proto, oxa_by_proto, sid)
            for sid in weapon_sids
        ]
    }
    report = render(result)
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(report, encoding="utf-8")
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(report, end="")
    print(f"\nFull report: {args.text_out.relative_to(ROOT).as_posix()}")
    print(f"JSON:        {args.json_out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
