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

# OXA's replacement weapons commonly keep a Vanilla SID while the defining
# WeaponGeneralSetup file is named after the real replacement platform.
GENERIC_SOURCE_STEMS = {
    "WeaponGeneralSetupPrototypes_OXA",
    "WeaponGeneralSetupPrototypes_DLC1",
    "WeaponGeneralSetupPrototypes_Deluxe",
    "WeaponGeneralSetupPrototypes_PreOrder",
    "WeaponGeneralSetupPrototypes_Ultimate",
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


def _replacement_labels(writes: list[Write]) -> list[str]:
    labels = set()
    for write in writes:
        source = write.source.replace("\\", "/")
        name = Path(source).stem
        prefix = "WeaponGeneralSetupPrototypes_def_"
        if name.startswith(prefix):
            labels.add(name[len(prefix):])
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
        replacement_labels = _replacement_labels(writes)
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
            else "OXA_WEAPON_REPLACEMENT" if replacement_labels
            else "OXA_PATCHED_VANILLA"
        )
        candidates.append({
            "sid": sid,
            "classification": classification,
            "replacement_labels": replacement_labels,
            "sources": header["sources"],
            "prototype_modes": header["modes"],
            "write_count": len(writes),
            "explicit_path_count": len(explicit_paths),
            "semantic_roots": semantic_roots,
        })

    new_sids = [x for x in candidates if x["classification"] == "OXA_NEW_SID"]
    replacements = [x for x in candidates if x["classification"] == "OXA_WEAPON_REPLACEMENT"]
    patched = [x for x in candidates if x["classification"] == "OXA_PATCHED_VANILLA"]

    return {
        "summary": {
            "oxa_prototypes": len(oxa_by_proto),
            "vanilla_prototypes": len(vanilla_by_proto),
            "weapon_candidates": len(candidates),
            "oxa_new_sid": len(new_sids),
            "oxa_weapon_replacements": len(replacements),
            "oxa_patched_vanilla": len(patched),
        },
        "oxa_new_sid": new_sids,
        "oxa_weapon_replacements": replacements,
        "oxa_patched_vanilla": patched,
    }


def _render_items(lines: list[str], items: list[dict], show_replacement: bool = False) -> None:
    if not items:
        lines.append("<none>")
        return
    for item in items:
        roots = ", ".join(item["semantic_roots"]) or "-"
        replacement = ""
        if show_replacement:
            replacement = " -> " + "/".join(item["replacement_labels"])
        lines.append(f"{item['sid']}{replacement} | writes={item['write_count']} | arrays={roots}")
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
        f"OXA weapon replacements: {s['oxa_weapon_replacements']}",
        f"Ordinary patched Vanilla weapons: {s['oxa_patched_vanilla']}",
        "",
        "OXA NEW WEAPON SIDS",
        "===================",
    ]
    _render_items(lines, result["oxa_new_sid"])

    lines += ["", "OXA WEAPON REPLACEMENTS", "======================="]
    _render_items(lines, result["oxa_weapon_replacements"], show_replacement=True)

    lines += ["", "ORDINARY OXA PATCHES TO VANILLA", "==============================="]
    _render_items(lines, result["oxa_patched_vanilla"])
    return "\n".join(lines).rstrip() + "\n"

