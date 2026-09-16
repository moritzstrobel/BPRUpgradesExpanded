from __future__ import annotations

import math
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CFG_ROOT = SCRIPT_DIR / "CFGGenerators"
COMMON_DIR = CFG_ROOT / "Common"
CLASS_DIRS = (CFG_ROOT / "AssaultRifles", CFG_ROOT / "SMGs", CFG_ROOT / "Shotguns", CFG_ROOT / "Pistols", CFG_ROOT / "Snipers", CFG_ROOT / "MachineGuns")
for module_dir in (COMMON_DIR, *CLASS_DIRS): sys.path.insert(0, str(module_dir))

import generate_assault_rifle_upgrades as ar
import generate_machine_gun_upgrades as machine_gun
import generate_pistol_upgrades as pistol
import generate_shotgun_upgrades as shotgun
import generate_smg_upgrades as smg
import generate_sniper_upgrades as sniper
from apply_module_layout import apply_layout_to_model
from dlc_weapon_modules import build_dlc_models
from smg_conversion_attachments import CONVERSION_ATTACHMENTS, attachment_block
from specialization_modules import build_shared_specializations, render_shared_effects
from unique_weapon_modules import add_unique_modules
from upgrade_build_model import UpgradeBuildModel
from upgrade_renderers import render_consolidated_upgrade_prototypes, render_dlc_general_setup_patch, render_final_general_setup_patch, render_technician_patch
from vanilla_upgrade_layout import DLC_ROOT, VANILLA_WEAPONS, _direct_child, _direct_scalar, _indexed_children, _refkey, _sid, _top_level_blocks

CONTENT_ROOT = SCRIPT_DIR.parent
UPGRADES_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
GENERAL_SETUP_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
WEAPON_PATH = CONTENT_ROOT / "GameLite/GameData/ItemPrototypes/WeaponPrototypes/WeaponPrototypes_patch_BPRUE.cfg"
NPC_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"
SHARED_EFFECT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_SharedSpecializationEffectPrototypes.cfg"
MACHINE_GUN_EFFECT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_MachineGunEffectPrototypes.cfg"
DLC_OUTPUT_ROOT = CONTENT_ROOT / "GameLite/DLCGameData"
MIN_SECTION_DISTANCE = 100.0; SECTION_NUDGE_STEP = 20.0; SECTION_NUDGE_RINGS = 12


def _shared_upgrades(configs: dict):
    specs = (
        (configs["pistol"]["families"], "pistol", "Pistol", pistol.TEMPLATE_SID, lambda _: pistol.IMAGE, pistol.ICON, "PistolShared"),
        (configs["smg"]["families"], "smg", "SMG", smg.TEMPLATE_SID, lambda _: smg.IMAGE, smg.ICON, "SMGShared"),
        (configs["ar"]["families"], "assault_rifle", "AR", ar.MODULE_TEMPLATE_SID, lambda family: family["image"], ar.DEFAULT_ICON, "ARShared"),
        (configs["shotgun"]["families"], "shotgun", "SG", shotgun.TEMPLATE_SID, lambda _: shotgun.IMAGE, shotgun.ICON, "SGShared"),
        (configs["sniper"]["families"], "sniper", "Sniper", sniper.TEMPLATE_SID, lambda _: sniper.IMAGE, sniper.ICON, "SniperShared"),
        (configs["machine_gun"]["families"], "machine_gun", "MG", machine_gun.TEMPLATE_SID, lambda _: machine_gun.IMAGE, machine_gun.ICON, "MGShared"),
    )
    result = []
    for families, class_key, weapon_class, template, image_fn, icon, namespace in specs:
        result.extend(build_shared_specializations(families=families, class_key=class_key, weapon_class=weapon_class, template_sid=template, image_for_family=image_fn, icon=icon, sid_namespace=namespace))
    return result


def build_model() -> tuple[UpgradeBuildModel, dict]:
    configs = {"ar": ar.load_config(), "smg": smg.load_config(), "shotgun": shotgun.cfg(), "pistol": pistol.load_config(), "sniper": sniper.load_config(), "machine_gun": machine_gun.load_config()}
    model = UpgradeBuildModel()
    for upgrades in (ar.build_upgrades(configs["ar"]), smg.build_upgrades(configs["smg"]), shotgun.build_upgrades(configs["shotgun"]), pistol.build_upgrades(configs["pistol"]), sniper.build_upgrades(configs["sniper"]), machine_gun.build_upgrades(configs["machine_gun"]), _shared_upgrades(configs)): model.extend(upgrades)
    unique_count = add_unique_modules(model, configs); print(f"Added {unique_count} Unique weapon module instances from central registry")
    ar.configure_general_setups(configs["ar"], model); model.validate(); apply_layout_to_model(model); model.validate()
    return model, configs


def build_dlc_outputs(source_model: UpgradeBuildModel, configs: dict) -> dict[str, UpgradeBuildModel]:
    models = build_dlc_models(source_model, configs)
    for pack, model in models.items():
        apply_layout_to_model(model, content_pack=pack); model.validate(); print(f"Built DLC {pack}: {model.summary()}")
    return models


def validate_rendered_outputs(model, upgrade_text, setup_text, npc_text=None):
    errors = []
    for upgrade in model.upgrades:
        if upgrade_text.count(f"{upgrade.sid} : struct.begin") != 1: errors.append(f"{upgrade.sid}: expected exactly one prototype definition")
        for setup_sid in upgrade.general_setup_sids:
            if setup_sid not in setup_text or upgrade.sid not in setup_text: errors.append(f"{upgrade.sid}: missing GeneralSetup registration for {setup_sid}")
        if npc_text is not None and upgrade.technician and upgrade.sid not in npc_text: errors.append(f"{upgrade.sid}: missing technician registration")
    if errors: raise ValueError("Generated upgrade output validation failed:\n  - " + "\n  - ".join(errors))


def _float_scalar(block, name):
    raw = _direct_scalar(block, name)
    if raw is None: return None
    try: return float(raw)
    except ValueError: return None


def _section_index(section):
    match = re.match(r"\s*\[(\d+)\]", section[0])
    if not match: raise ValueError(f"Invalid SectionSettings entry: {section[0]!r}")
    return int(match.group(1))


def _far_enough(point, occupied): return all(math.dist(point, other) >= MIN_SECTION_DISTANCE for other in occupied)

def _resolve_section_position(origin, occupied):
    if _far_enough(origin, occupied): return origin
    directions = ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
    for ring in range(1, SECTION_NUDGE_RINGS + 1):
        offset = ring * SECTION_NUDGE_STEP; candidates = []
        for dx, dy in directions:
            point = (origin[0] + dx * offset, origin[1] + dy * offset)
            if _far_enough(point, occupied): candidates.append((math.dist(origin, point), *point))
        if candidates:
            _, x, y = min(candidates); return x, y
    raise ValueError(f"Could not separate weapon section hotspot at {origin}")


def _blocks_by_sid(path: Path) -> dict[str, list[str]]:
    if not path.exists(): return {}
    return {_sid(block): block for block in _top_level_blocks(path.read_text(encoding="utf-8"))}


def _effective_scalar(sid: str, name: str, primary: dict[str, list[str]], fallback: dict[str, list[str]]) -> str | None:
    seen = set(); current = sid
    while current and current not in seen:
        seen.add(current); block = primary.get(current) or fallback.get(current)
        if not block: return None
        value = _direct_scalar(block, name)
        if value is not None: return value
        current = _refkey(block)
    return None


def _effective_section_settings(sid: str, primary: dict[str, list[str]], fallback: dict[str, list[str]]) -> list[str] | None:
    seen = set(); current = sid
    while current and current not in seen:
        seen.add(current); block = primary.get(current) or fallback.get(current)
        if not block: return None
        settings = _direct_child(block, "SectionSettings")
        if settings: return settings
        current = _refkey(block)
    return None


def render_weapon_sections_patch(model: UpgradeBuildModel, *, content_pack: str | None = None) -> str:
    """Enable inherited disabled upgrade sections for every weapon targeted by the model.

    Base/Unique weapons are resolved through Vanilla inheritance. DLC weapons are
    resolved through their pack-local ItemPrototypes first and then through the
    Vanilla WeaponPrototypes fallback. The patch is emitted against the actual
    child weapon SID, so inherited SectionSettings can be enabled without
    modifying the parent weapon globally.
    """
    wanted_setups = set(model.by_general_setup()); vanilla = _blocks_by_sid(VANILLA_WEAPONS)
    source_path = DLC_ROOT / content_pack / "ItemPrototypes.cfg" if content_pack else VANILLA_WEAPONS
    primary = _blocks_by_sid(source_path); fallback = vanilla if content_pack else {}
    patches = []; enabled_count = moved_count = weapon_count = 0

    for weapon_sid, weapon in primary.items():
        setup_sid = _effective_scalar(weapon_sid, "GeneralWeaponSetup", primary, fallback)
        if setup_sid not in wanted_setups: continue
        settings = _effective_section_settings(weapon_sid, primary, fallback)
        if not settings: continue
        sections = []
        for section in _indexed_children(settings):
            target = _direct_scalar(section, "UpgradeTargetPartType"); left = _float_scalar(section, "LeftPosition"); top = _float_scalar(section, "TopPosition")
            if target is None or left is None or top is None: continue
            sections.append({"index": _section_index(section), "enabled": (_direct_scalar(section, "SectionIsEnabled") or "").lower() == "true", "origin": (left, top)})
        occupied = [entry["origin"] for entry in sections if entry["enabled"]]; changed = []
        for entry in sections:
            if entry["enabled"]: continue
            position = _resolve_section_position(entry["origin"], occupied); occupied.append(position); moved = position != entry["origin"]
            changed.append((entry, position, moved)); enabled_count += 1; moved_count += int(moved)
        if not changed: continue
        weapon_count += 1
        lines = [f"{weapon_sid} : struct.begin {{bpatch}}", "   SectionSettings : struct.begin {bpatch}"]
        for entry, position, moved in changed:
            lines += [f"      [{entry['index']}] : struct.begin {{bpatch}}", "         SectionIsEnabled = true"]
            if moved: lines += [f"         LeftPosition = {position[0]:.6f}", f"         TopPosition = {position[1]:.6f}"]
            lines.append("      struct.end")
        lines += ["   struct.end", "struct.end", ""]; patches.extend(lines)

    scope = f"DLCGameData/{content_pack}" if content_pack else "BaseGame"
    header = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", f"// Scope: {scope}", "// Enables inherited predefined weapon upgrade sections for BPRUE.", f"// Minimum hotspot distance: {MIN_SECTION_DISTANCE:.1f}", f"// Patched weapons: {weapon_count}; enabled disabled sections: {enabled_count}; repositioned collisions: {moved_count}", "// -----------------------------------------------------------------------------", ""]
    return "\n".join(header + patches).rstrip() + "\n"


def write(path, content): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8"); print(f"Generated {path}")


def main():
    print("Building unified weapon upgrade model")
    model, configs = build_model(); print(f"Built {model.summary()}")
    dlc_models = build_dlc_outputs(model, configs)
    attachments = {sid: attachment_block(data) for sid, data in CONVERSION_ATTACHMENTS.items()}
    upgrade_text = render_consolidated_upgrade_prototypes(model); setup_text = render_final_general_setup_patch(model, attachments); npc_text = render_technician_patch(model); weapon_text = render_weapon_sections_patch(model)
    validate_rendered_outputs(model, upgrade_text, setup_text, npc_text)
    write(UPGRADES_PATH, upgrade_text); write(GENERAL_SETUP_PATH, setup_text); write(WEAPON_PATH, weapon_text); write(NPC_PATH, npc_text)

    for pack, dlc_model in sorted(dlc_models.items()):
        dlc_upgrade_text = render_consolidated_upgrade_prototypes(dlc_model); dlc_setup_text = render_dlc_general_setup_patch(dlc_model, pack); dlc_weapon_text = render_weapon_sections_patch(dlc_model, content_pack=pack)
        validate_rendered_outputs(dlc_model, dlc_upgrade_text, dlc_setup_text)
        pack_root = DLC_OUTPUT_ROOT / pack
        write(pack_root / "UpgradePrototypes/UpgradePrototypes_patch_BPRUE.cfg", dlc_upgrade_text)
        write(pack_root / "WeaponData/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg", dlc_setup_text)
        write(pack_root / "ItemPrototypes_patch_BPRUE.cfg", dlc_weapon_text)

    write(ar.EFFECT_OUTPUT_PATH, ar.render_effect_patch(configs["ar"])); write(smg.EFFECT_OUTPUT_PATH, smg.render_effects()); write(shotgun.EFFECT_OUTPUT, shotgun.render_effects()); write(pistol.EFFECT_OUTPUT, pistol.render_effects()); write(sniper.EFFECT_OUTPUT, sniper.render_effects()); write(MACHINE_GUN_EFFECT_PATH, machine_gun.render_effects()); write(SHARED_EFFECT_PATH, render_shared_effects())
    print(f"Validated and rendered {len(model.upgrades)} base/Unique upgrades plus {sum(len(m.upgrades) for m in dlc_models.values())} DLC upgrades.")


if __name__ == "__main__": main()
