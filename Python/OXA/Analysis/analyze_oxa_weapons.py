from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

# Reuse the proven CFG parser so OXA discovery follows the same prototype
# interpretation as the existing compatibility tooling.
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Python" / "Analysis"))

from analyze_oxa_conflicts import Write, collect, collect_vanilla  # noqa: E402


DEFAULT_OXA_ROOT = ROOT / "Python/VanillaReference/OxaData"
DEFAULT_VANILLA_ROOT = ROOT / "Python/VanillaReference"
DEFAULT_TEXT_OUT = ROOT / "Python/OXA/Reports/oxa_weapons.txt"
DEFAULT_JSON_OUT = ROOT / "Python/OXA/Reports/oxa_weapons.json"

WEAPON_PATH_HINTS = (
    "/WeaponData/",
    "/WeaponGeneralSetupPrototypes/",
)
WEAPON_SIGNAL_PATHS = {
    "UpgradePrototypeSIDs",
    "CompatibleAttachments",
    "AmmoPrototypeSIDs",
    "DefaultAmmoPrototypeSID",
    "WeaponType",
}


def _prototype_nodes(writes: list[Write]) -> dict[str, list[Write]]:
    result: dict[str, list[Write]] = defaultdict(list)
    for write in writes:
        result[write.prototype].append(write)
    return result


def _source_is_weapon(source: str) -> bool:
    normalized = "/" + source.replace("\\", "/")
    return any(hint in normalized for hint in WEAPON_PATH_HINTS)


def _looks_like_weapon(writes: list[Write]) -> bool:
    if any(_source_is_weapon(w.source) for w in writes):
        return True
    top_paths = {w.path.split(".", 1)[0] for w in writes if w.path != "<prototype>"}
    return bool(top_paths & WEAPON_SIGNAL_PATHS)


def _prototype_header(writes: list[Write]) -> dict:
    nodes = [w for w in writes if w.path == "<prototype>" and w.kind == "prototype"]
    return {
        "sources": sorted({w.source for w in writes}),
        "modes": sorted({mode for w in nodes for mode in w.modes}),
    }


def discover(oxa_root: Path, vanilla_root: Path) -> dict:
    oxa = collect(oxa_root)
    vanilla = collect_vanilla(vanilla_root)

    oxa_by_proto = _prototype_nodes(oxa)
    vanilla_by_proto = _prototype_nodes(vanilla)
    vanilla_ids = set(vanilla_by_proto)

    candidates = []
    for sid, writes in sorted(oxa_by_proto.items()):
        if not _looks_like_weapon(writes):
            continue

        header = _prototype_header(writes)
        is_new = sid not in vanilla_ids
        explicit_paths = sorted({w.path for w in writes if w.path != "<prototype>"})
        semantic_roots = sorted({
            w.path.split(".", 1)[0]
            for w in writes
            if w.path != "<prototype>"
            and w.path.split(".", 1)[0] in {
                "UpgradePrototypeSIDs", "CompatibleAttachments",
                "AttachPrototypeSIDs", "EffectPrototypeSIDs",
            }
        })

        candidates.append({
            "sid": sid,
            "classification": "OXA_ONLY" if is_new else "OXA_PATCHES_VANILLA",
            "sources": header["sources"],
            "prototype_modes": header["modes"],
            "write_count": len(writes),
            "explicit_path_count": len(explicit_paths),
            "semantic_roots": semantic_roots,
        })

    oxa_only = [x for x in candidates if x["classification"] == "OXA_ONLY"]
    patched = [x for x in candidates if x["classification"] == "OXA_PATCHES_VANILLA"]

    return {
        "summary": {
            "oxa_prototypes": len(oxa_by_proto),
            "vanilla_prototypes": len(vanilla_by_proto),
            "weapon_candidates": len(candidates),
            "oxa_only_weapon_candidates": len(oxa_only),
            "patched_vanilla_weapon_candidates": len(patched),
        },
        "oxa_only": oxa_only,
        "patched_vanilla": patched,
    }


def render(result: dict) -> str:
    s = result["summary"]
    lines = [
        "OXA weapon inventory",
        "====================",
        f"OXA prototypes: {s['oxa_prototypes']}",
        f"Vanilla/DLC prototypes: {s['vanilla_prototypes']}",
        f"Weapon candidates: {s['weapon_candidates']}",
        f"OXA-only candidates: {s['oxa_only_weapon_candidates']}",
        f"Patched Vanilla candidates: {s['patched_vanilla_weapon_candidates']}",
        "",
        "OXA-ONLY WEAPON CANDIDATES",
        "==========================",
    ]

    if not result["oxa_only"]:
        lines.append("<none>")
    for item in result["oxa_only"]:
        roots = ", ".join(item["semantic_roots"]) or "-"
        lines.append(
            f"{item['sid']} | writes={item['write_count']} | arrays={roots}"
        )
        for source in item["sources"]:
            lines.append(f"  source: {source}")

    lines += ["", "PATCHED VANILLA WEAPON CANDIDATES", "================================="]
    if not result["patched_vanilla"]:
        lines.append("<none>")
    for item in result["patched_vanilla"]:
        roots = ", ".join(item["semantic_roots"]) or "-"
        lines.append(
            f"{item['sid']} | writes={item['write_count']} | arrays={roots}"
        )
        for source in item["sources"]:
            lines.append(f"  source: {source}")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory OXA weapon prototypes and separate OXA-only weapons from "
            "patches to Vanilla/DLC weapons. This is discovery only; it does not "
            "generate BPRUE upgrades."
        )
    )
    parser.add_argument("--oxa-root", type=Path, default=DEFAULT_OXA_ROOT)
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    parser.add_argument("--text-out", type=Path, default=DEFAULT_TEXT_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args()

    result = discover(args.oxa_root, args.vanilla_root)
    text_report = render(result)

    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(text_report, encoding="utf-8")
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(text_report, end="")
    print(f"\nFull report: {args.text_out.relative_to(ROOT).as_posix()}")
    print(f"JSON:        {args.json_out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
