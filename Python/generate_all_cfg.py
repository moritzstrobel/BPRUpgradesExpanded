from __future__ import annotations

import math
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CFG_ROOT = SCRIPT_DIR / "CFGGenerators"
COMMON_DIR = CFG_ROOT / "Common"
CLASS_DIRS = (
    CFG_ROOT / "AssaultRifles",
    CFG_ROOT / "SMGs",
    CFG_ROOT / "Shotguns",
    CFG_ROOT / "Pistols",
    CFG_ROOT / "Snipers",
)
for module_dir in (COMMON_DIR, *CLASS_DIRS):
    sys.path.insert(0, str(module_dir))

import generate_assault_rifle_upgrades as ar
import generate_pistol_upgrades as pistol
import generate_shotgun_upgrades as shotgun
import generate_smg_upgrades as smg
import generate_sniper_upgrades as sniper
from apply_module_layout import apply_layout_to_model
from smg_conversion_attachments import CONVERSION_ATTACHMENTS, attachment_block
from upgrade_build_model import UpgradeBuildModel
from upgrade_renderers import (
    render_consolidated_upgrade_prototypes,
    render_final_general_setup_patch,
    render_technician_patch,
)
from vanilla_upgrade_layout import VANILLA_WEAPONS, _direct_child, _direct_scalar, _indexed_children, _sid, _top_level_blocks

CONTENT_ROOT = SCRIPT_DIR.parent
UPGRADES_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
GENERAL_SETUP_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
WEAPON_PATH = CONTENT_ROOT / "GameLite/GameData/ItemPrototypes/WeaponPrototypes/WeaponPrototypes_patch_BPRUE.cfg"
NPC_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"

# Section hotspot coordinates are screen-relative. Keep newly enabled sections at
# least this far from every already active/enabled hotspot.
MIN_SECTION_DISTANCE = 40.0
SECTION_NUDGE_STEP = 20.0
SECTION_NUDGE_RINGS = 12


def build_model() -> tuple[UpgradeBuildModel, dict]:
    configs = {"ar": ar.load_config(), "smg": smg.load_config(), "shotgun": shotgun.cfg(), "pistol": pistol.load_config(), "sniper": sniper.load_config()}
    model = UpgradeBuildModel()
    model.extend(ar.build_upgrades(configs["ar"]))
    model.extend(smg.build_upgrades(configs["smg"]))
    model.extend(shotgun.build_upgrades(configs["shotgun"]))
    model.extend(pistol.build_upgrades(configs["pistol"]))
    model.extend(sniper.build_upgrades(configs["sniper"]))
    ar.configure_general_setups(configs["ar"], model)
    model.validate()
    apply_layout_to_model(model)
    model.validate()
    return model, configs


def validate_rendered_outputs(model: UpgradeBuildModel, upgrade_text: str, setup_text: str, npc_text: str) -> None:
    errors: list[str] = []
    for upgrade in model.upgrades:
        count = upgrade_text.count(f"{upgrade.sid} : struct.begin")
        if count != 1:
            errors.append(f"{upgrade.sid}: expected exactly one prototype definition, found {count}")
        for setup_sid in upgrade.general_setup_sids:
            if setup_sid not in setup_text or upgrade.sid not in setup_text:
                errors.append(f"{upgrade.sid}: missing GeneralSetup registration for {setup_sid}")
        if upgrade.technician and upgrade.sid not in npc_text:
            errors.append(f"{upgrade.sid}: missing technician registration")
    if errors:
        raise ValueError("Generated upgrade output validation failed:\n  - " + "\n  - ".join(errors))


def _float_scalar(block: list[str], name: str) -> float | None:
    raw = _direct_scalar(block, name)
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _section_index(section: list[str]) -> int:
    match = re.match(r"\s*\[(\d+)\]", section[0])
    if not match:
        raise ValueError(f"Invalid SectionSettings entry: {section[0]!r}")
    return int(match.group(1))


def _far_enough(point: tuple[float, float], occupied: list[tuple[float, float]]) -> bool:
    return all(math.dist(point, other) >= MIN_SECTION_DISTANCE for other in occupied)


def _resolve_section_position(origin: tuple[float, float], occupied: list[tuple[float, float]]) -> tuple[float, float]:
    """Return the closest collision-free hotspot, preserving Vanilla when possible."""
    if _far_enough(origin, occupied):
        return origin

    # Search symmetric rings around the Vanilla position. Axis/diagonal offsets
    # are deterministic and keep corrections small instead of drifting hotspots.
    directions = (
        (1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
        (1.0, 1.0), (1.0, -1.0), (-1.0, 1.0), (-1.0, -1.0),
    )
    candidates: list[tuple[float, float, float]] = []
    for ring in range(1, SECTION_NUDGE_RINGS + 1):
        offset = ring * SECTION_NUDGE_STEP
        for dx, dy in directions:
            point = (origin[0] + dx * offset, origin[1] + dy * offset)
            if _far_enough(point, occupied):
                candidates.append((math.dist(origin, point), point[0], point[1]))
        if candidates:
            _, x, y = min(candidates)
            return x, y

    raise ValueError(f"Could not separate weapon section hotspot at {origin}")


def render_weapon_sections_patch(model: UpgradeBuildModel) -> str:
    """Enable all five predefined sections for every BPRUE weapon.

    Vanilla-active hotspots are immutable. Disabled sections are enabled in their
    Vanilla position unless that would overlap another active/enabled hotspot; only
    then are LeftPosition/TopPosition overridden with the nearest safe position.
    """
    wanted_setups = set(model.by_general_setup())
    patches: list[str] = []
    enabled_count = 0
    moved_count = 0

    for weapon in _top_level_blocks(VANILLA_WEAPONS.read_text(encoding="utf-8")):
        general_setup = _direct_scalar(weapon, "GeneralWeaponSetup")
        if general_setup not in wanted_setups:
            continue
        settings = _direct_child(weapon, "SectionSettings")
        if not settings:
            continue

        sections = []
        for section in _indexed_children(settings):
            target_raw = _direct_scalar(section, "UpgradeTargetPartType")
            left = _float_scalar(section, "LeftPosition")
            top = _float_scalar(section, "TopPosition")
            if target_raw is None or left is None or top is None:
                continue
            sections.append({
                "index": _section_index(section),
                "target": target_raw.rsplit("::", 1)[-1],
                "enabled": (_direct_scalar(section, "SectionIsEnabled") or "").lower() == "true",
                "origin": (left, top),
            })

        occupied = [entry["origin"] for entry in sections if entry["enabled"]]
        changed = []
        for entry in sections:
            if entry["enabled"]:
                continue
            position = _resolve_section_position(entry["origin"], occupied)
            occupied.append(position)
            moved = position != entry["origin"]
            changed.append((entry, position, moved))
            enabled_count += 1
            moved_count += int(moved)

        if not changed:
            continue

        lines = [f"{_sid(weapon)} : struct.begin {{bpatch}}", "   SectionSettings : struct.begin {bpatch}"]
        for entry, position, moved in changed:
            lines.append(f"      [{entry['index']}] : struct.begin {{bpatch}}")
            lines.append("         SectionIsEnabled = true")
            if moved:
                lines.append(f"         LeftPosition = {position[0]:.6f}")
                lines.append(f"         TopPosition = {position[1]:.6f}")
            lines.append("      struct.end")
        lines += ["   struct.end", "struct.end", ""]
        patches.extend(lines)

    header = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Enables predefined Vanilla weapon upgrade sections for BPRUE.",
        f"// Minimum hotspot distance: {MIN_SECTION_DISTANCE:.1f}",
        f"// Enabled disabled sections: {enabled_count}; repositioned collisions: {moved_count}",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    return "\n".join(header + patches).rstrip() + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Generated {path}")


def main() -> None:
    print("Building unified weapon upgrade model")
    model, configs = build_model()
    print(f"Built {model.summary()}")

    attachments = {sid: attachment_block(data) for sid, data in CONVERSION_ATTACHMENTS.items()}
    upgrade_text = render_consolidated_upgrade_prototypes(model)
    setup_text = render_final_general_setup_patch(model, attachments)
    npc_text = render_technician_patch(model)
    weapon_text = render_weapon_sections_patch(model)
    validate_rendered_outputs(model, upgrade_text, setup_text, npc_text)

    write(UPGRADES_PATH, upgrade_text)
    write(GENERAL_SETUP_PATH, setup_text)
    write(WEAPON_PATH, weapon_text)
    write(NPC_PATH, npc_text)
    write(ar.EFFECT_OUTPUT_PATH, ar.render_effect_patch(configs["ar"]))
    write(smg.EFFECT_OUTPUT_PATH, smg.render_effects())
    write(shotgun.EFFECT_OUTPUT, shotgun.render_effects())
    write(pistol.EFFECT_OUTPUT, pistol.render_effects())
    write(sniper.EFFECT_OUTPUT, sniper.render_effects())
    print(f"Validated and rendered {len(model.upgrades)} upgrades in one build pass.")


if __name__ == "__main__":
    main()
