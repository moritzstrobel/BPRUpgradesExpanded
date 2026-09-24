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

# A def_<platform>.cfg filename is useful only when compared with the file
# family that defines the same SID in Vanilla/DLC. On its own it merely names
# OXA's implementation file and is not evidence of a replacement.


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


def _weapon_family_labels(writes: list[Write]) -> list[str]:
    labels = set()
    for write in writes:
        source = write.source.replace("\\", "/")
        if "/WeaponGeneralSetupPrototypes/" not in ("/" + source):
            continue
        stem = Path(source).stem
        prefix = "WeaponGeneralSetupPrototypes_def_"
        if stem.startswith(prefix):
            labels.add(stem[len(prefix):])
        else:
            # Generic Vanilla/DLC/OXA files are still meaningful for comparison:
            # equal generic stems mean no file-family transition; a def_* on only
            # one side is a useful platform-change signal.
            labels.add(stem)
    return sorted(labels)


def _is_real_weapon_setup(writes: list[Write]) -> bool:
    return any("/WeaponGeneralSetupPrototypes/" in ("/" + w.source.replace("\\", "/")) for w in writes)


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
        if not _looks_like_weapon(writes) or not _is_real_weapon_setup(writes):
            continue

        header = _prototype_header(writes)
        is_new = sid not in vanilla_ids
        oxa_families = _weapon_family_labels(writes)
        vanilla_families = _weapon_family_labels(vanilla_by_proto.get(sid, []))
        family_changed = bool(vanilla_families and oxa_families and set(vanilla_families) != set(oxa_families))
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

        classification = (
            "OXA_NEW_SID" if is_new
            else "OXA_NEW_PLATFORM" if family_changed
            else "OXA_PATCHED_VANILLA"
        )
        candidates.append({
            "sid": sid,
            "classification": classification,
            "vanilla_families": vanilla_families,
            "oxa_families": oxa_families,
            "sources": header["sources"],
            "prototype_modes": header["modes"],
            "write_count": len(writes),
            "explicit_path_count": len(explicit_paths),
            "semantic_roots": semantic_roots,
        })

    new_sids = [x for x in candidates if x["classification"] == "OXA_NEW_SID"]
    new_platforms = [x for x in candidates if x["classification"] == "OXA_NEW_PLATFORM"]
    patched = [x for x in candidates if x["classification"] == "OXA_PATCHED_VANILLA"]

    return {
        "summary": {
            "oxa_prototypes": len(oxa_by_proto),
            "vanilla_prototypes": len(vanilla_by_proto),
            "weapon_candidates": len(candidates),
            "oxa_new_sid": len(new_sids),
            "oxa_new_platforms": len(new_platforms),
            "oxa_patched_vanilla": len(patched),
        },
        "oxa_new_sid": new_sids,
        "oxa_new_platforms": new_platforms,
        "oxa_patched_vanilla": patched,
    }


def _render_items(lines: list[str], items: list[dict], show_transition: bool = False) -> None:
    if not items:
        lines.append("<none>")
        return
    for item in items:
        roots = ", ".join(item["semantic_roots"]) or "-"
        transition = ""
        if show_transition:
            vanilla = "/".join(item["vanilla_families"]) or "?"
            oxa = "/".join(item["oxa_families"]) or "?"
            transition = f" | family: {vanilla} -> {oxa}"
        lines.append(f"{item['sid']}{transition} | writes={item['write_count']} | arrays={roots}")
        for source in item["sources"]:
            lines.append(f"  source: {source}")


def render(result: dict) -> str:
    s = result["summary"]
    lines = [
        "OXA weapon inventory",
        "====================",
        f"OXA prototypes: {s['oxa_prototypes']}",
        f"Vanilla/DLC prototypes: {s['vanilla_prototypes']}",
        f"Real weapon candidates: {s['weapon_candidates']}",
        f"New OXA SIDs: {s['oxa_new_sid']}",
        f"OXA new platforms: {s['oxa_new_platforms']}",
        f"Ordinary patched Vanilla weapons: {s['oxa_patched_vanilla']}",
        "",
        "OXA NEW WEAPON SIDS",
        "===================",
    ]
    _render_items(lines, result["oxa_new_sid"])

    lines += ["", "OXA NEW WEAPON PLATFORMS", "========================"]
    _render_items(lines, result["oxa_new_platforms"], show_transition=True)

    lines += ["", "ORDINARY OXA PATCHES TO VANILLA", "==============================="]
    _render_items(lines, result["oxa_patched_vanilla"])
    return "\n".join(lines).rstrip() + "\n"



def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inventory real OXA weapon setup prototypes and separate new SIDs, "
            "new weapon platforms, and ordinary Vanilla/DLC patches."
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
