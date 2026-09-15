from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
VANILLA_REFERENCE = PYTHON_ROOT / "VanillaReference" / "WeaponGeneralSetupPrototypes.cfg"
GENERAL_SETUP_DIR = CONTENT_ROOT / "GameLite" / "GameData" / "WeaponData" / "WeaponGeneralSetupPrototypes"
FINAL_PATH = GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
SPLIT_PATHS = [
    GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE_SMGModules.cfg",
    GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE_ShotgunModules.cfg",
    GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE_PistolModules.cfg",
    GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE_SniperModules.cfg",
]


def split_top_level_blocks(text: str, require_bpatch: bool = True) -> tuple[list[str], list[tuple[str, list[str]]]]:
    preamble: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] | None = None
    current_sid: str | None = None
    depth = 0

    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            is_top_level = not line.startswith((" ", "\t"))
            is_begin = ": struct.begin" in stripped
            is_patch = "{bpatch}" in stripped
            if is_top_level and is_begin and (is_patch or not require_bpatch):
                current = [line]
                current_sid = stripped.split(" :", 1)[0]
                depth = 1
            else:
                preamble.append(line)
            continue

        current.append(line)
        if "struct.begin" in stripped:
            depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0:
                blocks.append((current_sid or "", current))
                current = None
                current_sid = None

    if current is not None:
        raise ValueError(f"Unclosed GeneralSetup block: {current_sid}")
    return preamble, blocks


def direct_children(block: list[str]) -> tuple[list[str], OrderedDict[str, list[str]]]:
    scalars: list[str] = []
    children: OrderedDict[str, list[str]] = OrderedDict()
    i = 1
    while i < len(block) - 1:
        line = block[i]
        stripped = line.strip()
        if line.startswith("   ") and not line.startswith("      ") and " : struct.begin" in stripped:
            name = stripped.split(" :", 1)[0]
            child = [line]
            depth = 1
            i += 1
            while i < len(block) - 1 and depth:
                child.append(block[i])
                s = block[i].strip()
                if "struct.begin" in s:
                    depth += 1
                if s == "struct.end":
                    depth -= 1
                i += 1
            children[name] = child
            continue
        if stripped and line not in scalars:
            scalars.append(line)
        i += 1
    return scalars, children


def merge_child(existing: list[str], incoming: list[str]) -> list[str]:
    result = existing[:-1]
    seen = {line.strip() for line in result[1:] if line.strip()}
    for line in incoming[1:-1]:
        if line.strip() and line.strip() not in seen:
            result.append(line)
            seen.add(line.strip())
    result.append(existing[-1])
    return result


def merge_blocks(existing: list[str], incoming: list[str]) -> list[str]:
    scalars_a, children_a = direct_children(existing)
    scalars_b, children_b = direct_children(incoming)

    for scalar in scalars_b:
        if scalar.strip() and scalar not in scalars_a:
            scalars_a.append(scalar)
    for name, child in children_b.items():
        if name in children_a:
            children_a[name] = merge_child(children_a[name], child)
        else:
            children_a[name] = child

    result = [existing[0]]
    result.extend(scalars_a)
    for child in children_a.values():
        result.extend(child)
    result.append("struct.end")
    return result


def parse_upgrade_sids(child: list[str]) -> list[str]:
    sids: list[str] = []
    for line in child[1:-1]:
        match = re.match(r"\s*(?:\[[^\]]+\]|[^=]+)\s*=\s*([A-Za-z0-9_]+)\s*$", line)
        if match:
            sid = match.group(1)
            if sid not in sids:
                sids.append(sid)
    return sids


def render_complete_upgrade_child(vanilla_sids: list[str], bprue_sids: list[str]) -> list[str]:
    combined: list[str] = []
    for sid in [*vanilla_sids, *bprue_sids]:
        if sid not in combined:
            combined.append(sid)

    lines = ["   UpgradePrototypeSIDs : struct.begin {bpatch}"]
    # Use SID keys rather than numeric vanilla indexes. This keeps the generated
    # patch deterministic while explicitly carrying the complete vanilla+BPRUE set.
    lines.extend(f"      {sid} = {sid}" for sid in combined)
    lines.append("   struct.end")
    return lines


def load_vanilla_upgrade_sids() -> dict[str, list[str]]:
    if not VANILLA_REFERENCE.exists():
        raise FileNotFoundError(
            f"Missing vanilla reference: {VANILLA_REFERENCE}. "
            "Keep the current WeaponGeneralSetupPrototypes.cfg under Python/VanillaReference."
        )

    _, blocks = split_top_level_blocks(
        VANILLA_REFERENCE.read_text(encoding="utf-8"), require_bpatch=False
    )
    result: dict[str, list[str]] = {}
    for sid, block in blocks:
        _, children = direct_children(block)
        upgrade_child = children.get("UpgradePrototypeSIDs")
        if upgrade_child:
            result[sid] = parse_upgrade_sids(upgrade_child)
    return result


def inject_vanilla_upgrades(block: list[str], sid: str, vanilla: dict[str, list[str]]) -> list[str]:
    scalars, children = direct_children(block)
    bprue_child = children.get("UpgradePrototypeSIDs")
    if bprue_child is None:
        return block

    if sid not in vanilla:
        raise ValueError(
            f"BPRUE patches UpgradePrototypeSIDs for {sid}, but no vanilla UpgradePrototypeSIDs "
            f"were found in {VANILLA_REFERENCE}. Check the GeneralSetup SID/reference file."
        )

    children["UpgradePrototypeSIDs"] = render_complete_upgrade_child(
        vanilla[sid], parse_upgrade_sids(bprue_child)
    )

    result = [block[0]]
    result.extend(scalars)
    for child in children.values():
        result.extend(child)
    result.append("struct.end")
    return result


def main() -> None:
    if not FINAL_PATH.exists():
        raise FileNotFoundError(FINAL_PATH)

    vanilla = load_vanilla_upgrade_sids()
    sources = [FINAL_PATH, *[path for path in SPLIT_PATHS if path.exists()]]
    merged: OrderedDict[str, list[str]] = OrderedDict()

    for path in sources:
        _, blocks = split_top_level_blocks(path.read_text(encoding="utf-8"))
        for sid, block in blocks:
            if sid in merged:
                merged[sid] = merge_blocks(merged[sid], block)
            else:
                merged[sid] = block

    for sid, block in list(merged.items()):
        merged[sid] = inject_vanilla_upgrades(block, sid, vanilla)

    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Final owner of all BPRUE WeaponGeneralSetupPrototypes patches.",
        "// UpgradePrototypeSIDs contain the complete Vanilla + BPRUE set for each",
        "// patched weapon, sourced from Python/VanillaReference.",
        "// Generated by: generate_all_cfg.py / merge_weapon_general_setup_patches.py",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for block in merged.values():
        lines.extend(block)
        lines.append("")
    FINAL_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    for path in SPLIT_PATHS:
        if path.exists():
            path.unlink()

    print(f"Loaded vanilla upgrade lists for {len(vanilla)} GeneralSetup prototypes")
    print(f"Consolidated {len(merged)} weapon GeneralSetup patches into {FINAL_PATH}")


if __name__ == "__main__":
    main()
