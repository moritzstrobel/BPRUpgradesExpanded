from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = ROOT / "Python"
sys.path.insert(0, str(PYTHON_ROOT / "Analysis"))
sys.path.insert(0, str(PYTHON_ROOT))

from analyze_oxa_conflicts import (  # noqa: E402
    collect, collect_vanilla, _semantic_arrays, _writes_by_semantic_group,
    _apply_array_patch, _entry_identity,
)
from ExternalWeaponPacks.Analysis.analyze_weapon_packs import (  # noqa: E402
    DEFAULT_VANILLA_ROOT, game_data_roots, load_registry,
)

OXA_ROOT = DEFAULT_VANILLA_ROOT / "OxaData"
DEFAULT_OUTPUT = ROOT / "Compat/WeaponPacksOXA/GameLite"

# Compatibility families are deliberately capability parents, not CFG refkeys.
# They provide OXA attachment choices only. Foreign weapon geometry/stats remain untouched.
CALIBER_TOKENS = {
    "A545": ("545", "5.45"),
    "A556": ("556", "5.56"),
    "A762": ("762x39", "7.62x39"),
    "A762NATO": ("762x51", "7.62x51", "308"),
}
ALL_CALIBER_TOKENS = tuple(token for values in CALIBER_TOKENS.values() for token in values)

# OXA exposes some caliber alternatives through attachment fitting membership even
# when they are not part of the pseudo-parent's CompatibleAttachments delta.
# Keep this explicit and conservative: only verified OXA attachments belong here.
CALIBER_SUPPLEMENTS = {
    "A762": ("OXA_Mag_762x39_PMag30r",),
    "A762NATO": (),
}


def semantic_state(vanilla_writes, oxa_writes, prototype: str, root: str):
    key = (prototype, root)
    vg = _semantic_arrays(vanilla_writes)
    og = _writes_by_semantic_group(oxa_writes)
    base = {idx: dict(fields) for idx, fields in vg.get(key, {"entries": {}})["entries"].items()}
    effective, _ = _apply_array_patch(base, og.get(key, []), root)

    def by_id(state):
        result = {}
        for fields in state.values():
            identity = _entry_identity(root, fields)
            if identity is not None:
                result[identity] = dict(fields)
        return result

    return by_id(base), by_id(effective)


def source_weapon_sid(source_setup: str) -> str:
    return "GunArev_ST" if source_setup == "GunArev_ST_GS" else source_setup


def caliber_allowed(sid: str, caliber: str) -> bool:
    lower = sid.lower()
    present = {token for token in ALL_CALIBER_TOKENS if token.lower() in lower}
    if not present:
        return True
    allowed = {token.lower() for token in CALIBER_TOKENS.get(caliber, ())}
    return all(token.lower() in allowed for token in present)


def effective_fitting_entries(vanilla_writes, oxa_writes) -> dict[str, set[str]]:
    vg = _semantic_arrays(vanilla_writes)
    og = _writes_by_semantic_group(oxa_writes)
    keys = {key for key in set(vg) | set(og) if key[1] == "FittingWeaponsSIDs"}
    result = {}
    for prototype, root in keys:
        key = (prototype, root)
        base = {i: dict(f) for i, f in vg.get(key, {"entries": {}})["entries"].items()}
        state, _ = _apply_array_patch(base, og.get(key, []), root)
        result[prototype] = {
            identity for fields in state.values()
            if (identity := _entry_identity(root, fields)) is not None
        }
    return result


def pack_attachment_sids(spec: dict, vanilla_root: Path) -> set[str]:
    result = set()
    root = vanilla_root / spec["reference_root"]
    for game_data in game_data_roots(root):
        for path in game_data.rglob("*.cfg"):
            if "AttachPrototypes" not in path.as_posix():
                continue
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
            for line in text.splitlines():
                if ": struct.begin" in line and not line.lstrip().startswith("["):
                    result.add(line.split(":", 1)[0].strip())
    return result


def render_tree(fields: dict, indent=9) -> list[str]:
    tree = {}
    for path, value in fields.items():
        if path == "<value>":
            continue
        node = tree
        parts = path.split(".")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    def walk(node, level):
        lines, pad = [], " " * level
        for key, value in node.items():
            if isinstance(value, dict):
                lines.append(f"{pad}{key} : struct.begin")
                lines.extend(walk(value, level + 3))
                lines.append(f"{pad}struct.end")
            else:
                lines.append(f"{pad}{key} = {value}")
        return lines

    return walk(tree, indent)


def render_setup_patch(setup_sid: str, entries: list[dict]) -> str:
    lines = [f"{setup_sid} : struct.begin {{bpatch}}", "   CompatibleAttachments : struct.begin {bpatch}"]
    for entry in entries:
        lines.append("      [*] : struct.begin")
        lines.extend(render_tree(entry["fields"]))
        lines.append("      struct.end")
    lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def render_fitting_patch(attachment_sid: str, weapon_sids: list[str]) -> str:
    lines = [f"{attachment_sid} : struct.begin {{bpatch}}", "   FittingWeaponsSIDs : struct.begin {bpatch}"]
    lines.extend(f"      [*] = {sid}" for sid in weapon_sids)
    lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OXA attachment compatibility for registered external weapon packs.")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    parser.add_argument("--oxa-root", type=Path, default=OXA_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    vanilla = collect_vanilla(args.vanilla_root)
    oxa = collect(args.oxa_root)
    registry = load_registry()
    fitting_targets: dict[str, set[str]] = defaultdict(set)
    setup_outputs: dict[str, list[str]] = defaultdict(list)
    summary = []

    for pack_name, spec in registry["packs"].items():
        local_attachments = pack_attachment_sids(spec, args.vanilla_root)
        for weapon in spec["weapons"]:
            parent_setup = weapon["oxa_source_setup"]
            parent_weapon = source_weapon_sid(parent_setup)
            base, effective = semantic_state(vanilla, oxa, parent_setup, "CompatibleAttachments")
            added = set(effective) - set(base)

            # Only inherit OXA additions. Parent-specific modifications/removals contain
            # sockets, meshes and icons for the parent weapon and are unsafe to transplant.
            selected = sorted(sid for sid in added if caliber_allowed(sid, weapon["base_caliber"]))
            entries = []
            for sid in selected:
                fields = dict(effective[sid])
                fields["AttachPrototypeSID"] = sid
                entries.append({"sid": sid, "fields": fields})
                fitting_targets[sid].add(weapon["weapon_sid"])

            setup_outputs[pack_name].append(render_setup_patch(weapon["general_setup_sid"], entries))
            summary.append((pack_name, weapon["weapon_sid"], parent_weapon, weapon["base_caliber"], len(added), len(selected), len(supplements)))

    for pack_name, chunks in setup_outputs.items():
        root = args.output_root / pack_name / "GameData"
        setup_file = root / "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_OXA_WeaponPack.cfg"
        setup_file.parent.mkdir(parents=True, exist_ok=True)
        setup_file.write_text(
            "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND\n"
            "// OXA additions inherited through BPRUE pseudo-parent metadata.\n"
            "// Parent modifications/removals are intentionally not transplanted.\n\n"
            + "\n".join(chunks), encoding="utf-8"
        )

    # OXA attachment prototypes live in OXA's GameData and can be patched by SID.
    fitting_file = args.output_root / "Shared/GameData/ItemPrototypes/AttachPrototypes/AttachPrototypes_patch_BPRUE_OXA_WeaponPack.cfg"
    fitting_file.parent.mkdir(parents=True, exist_ok=True)
    fitting_file.write_text(
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND\n"
        "// Reverse fitting links for OXA attachments on external weapon packs.\n\n"
        + "\n".join(render_fitting_patch(sid, sorted(weapons)) for sid, weapons in sorted(fitting_targets.items())),
        encoding="utf-8",
    )

    print("BPRUE x OXA x external weapon packs")
    print("===================================")
    for pack, weapon, parent, caliber, available, selected in summary:
        print(f"{pack}: {weapon} <- {parent} [{caliber}] OXA additions={available}, selected={selected}")
    print(f"Unique OXA attachments patched: {len(fitting_targets)}")
    print(f"Output: {args.output_root.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
