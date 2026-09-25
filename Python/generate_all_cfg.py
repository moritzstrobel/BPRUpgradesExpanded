from __future__ import annotations

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMON = ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(COMMON))

from apply_module_layout import apply_layout_to_model
from dlc_weapon_modules import build_dlc_models, render_dlc_signature_effects
from edition_weapon_modules import build_edition_models
from upgrade_build_model import UpgradeBuildModel
from upgrade_renderers import (
    render_consolidated_upgrade_prototypes,
    render_dlc_general_setup_patch,
    render_final_general_setup_patch,
    render_technician_patch,
)
from unique_weapon_modules import add_unique_modules, add_unique_signatures, render_unique_signature_effects
from vanilla_upgrade_layout import DLC_ROOT, _direct_child, _direct_scalar, _indexed_children, _refkey, _sid, _top_level_blocks, render_vanilla_compaction_patch

from CFGGenerators.AssaultRifles import generate_assault_rifle_upgrades as ar
from CFGGenerators.MachineGuns import generate_machine_gun_upgrades as machine_gun
from CFGGenerators.Pistols import generate_pistol_upgrades as pistol
from CFGGenerators.Shotguns import generate_shotgun_upgrades as shotgun
from CFGGenerators.SMGs import generate_smg_upgrades as smg
from CFGGenerators.SMGs.smg_conversion_attachments import CONVERSION_ATTACHMENTS, attachment_block
from CFGGenerators.SMGs.pistol_conversion_variants import PISTOL_CONVERSION_VARIANTS
from CFGGenerators.Snipers import generate_sniper_upgrades as sniper
from CFGGenerators.Common.shared_effects import render_shared_effects
from CFGGenerators.Common.shared_upgrades import build_shared_upgrades

CONTENT_ROOT = ROOT.parent
VANILLA_ROOT = ROOT / "VanillaReference"
VANILLA_WEAPONS = VANILLA_ROOT / "WeaponPrototypes.cfg"
DLC_OUTPUT_ROOT = CONTENT_ROOT / "GameLite/DLCGameData"
EDITIONS_OUTPUT_ROOT = CONTENT_ROOT / "Editions/GameLite/DLCGameData"
UPGRADES_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
GENERAL_SETUP_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
WEAPON_PATH = CONTENT_ROOT / "GameLite/GameData/ItemPrototypes/WeaponPrototypes/WeaponPrototypes_patch_BPRUE.cfg"
CONVERSION_WEAPON_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/ItemPrototypes/WeaponPrototypes/BPRUE_WeaponPrototypes.cfg"
NPC_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"
VANILLA_COMPACTION_PATH = CONTENT_ROOT / "GameLite/GameData/UpgradePrototypes/UpgradePrototypes_patch_BPRUE.cfg"
VANILLA_EFFECT_UI_PATH = CONTENT_ROOT / "GameLite/GameData/EffectPrototypes/EffectPrototypes_patch_BPRUE_UI.cfg"
MACHINE_GUN_EFFECT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_MachineGunEffectPrototypes.cfg"
SHARED_EFFECT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_SharedEffectPrototypes.cfg"
UNIQUE_SIGNATURE_EFFECT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_UniqueSignatureEffectPrototypes.cfg"
MIN_SECTION_DISTANCE = 80.0
SECTION_NUDGE_STEP = 20.0
SECTION_NUDGE_RINGS = 12
SECTION_SEARCH_DIRECTIONS = 16

VANILLA_EFFECT_LOCALIZATION_OVERRIDES = {
    "RecoilDown10Effect": "bprue_recoil",
    "RecoilDown15Effect": "bprue_recoil",
    "WeightDown15Effect": "bprue_weight",
    "DistanceDropOffLengthPos20Effect": "bprue_effective_range",
    "FlatnessUp10Effect": "bprue_effective_range",
    "FlatnessUp15Effect": "bprue_effective_range",
}
VANILLA_TECHNICAL_EFFECTS_HIDDEN_FROM_UI = (
    "ChangeCaliber045Effect",
    "ChangeCaliber762Effect",
    "ChangeCaliber918Effect",
    "ChangeCaliber919Effect",
    "ChangeFireTypeEffectBurstAuto",
    "ChangeFireTypeEffectSemiAuto",
)


def _shared_upgrades(configs):
    return build_shared_upgrades(configs)


def build_model(*, apply_layout: bool = True) -> tuple[UpgradeBuildModel, dict]:
    configs = {"ar": ar.load_config(), "smg": smg.load_config(), "shotgun": shotgun.cfg(), "pistol": pistol.load_config(), "sniper": sniper.load_config(), "machine_gun": machine_gun.load_config()}
    model = UpgradeBuildModel()
    for upgrades in (ar.build_upgrades(configs["ar"]), smg.build_upgrades(configs["smg"]), shotgun.build_upgrades(configs["shotgun"]), pistol.build_upgrades(configs["pistol"]), sniper.build_upgrades(configs["sniper"]), machine_gun.build_upgrades(configs["machine_gun"]), _shared_upgrades(configs)): model.extend(upgrades)
    unique_count = add_unique_modules(model, configs); print(f"Added {unique_count} Unique weapon module instances from central registry")
    signature_count = add_unique_signatures(model); print(f"Added {signature_count} Unique signature modules")
    ar.configure_general_setups(configs["ar"], model); model.validate()
    if apply_layout:
        apply_layout_to_model(model); model.validate()
    return model, configs


def build_dlc_outputs(source_model: UpgradeBuildModel, configs: dict) -> dict[str, UpgradeBuildModel]:
    models = build_dlc_models(source_model, configs)
    for pack, model in models.items():
        apply_layout_to_model(model, content_pack=pack); model.validate(); print(f"Built DLC {pack}: {model.summary()}")
    return models


def build_edition_outputs(source_model: UpgradeBuildModel, configs: dict) -> dict[str, UpgradeBuildModel]:
    models = build_edition_models(source_model, configs)
    for pack, model in models.items():
        apply_layout_to_model(model, content_pack=pack); model.validate(); print(f"Built Edition {pack}: {model.summary()}")
    return models


def _render_content_pack_outputs(models: dict[str, UpgradeBuildModel], output_root: Path, *, signature_effects: bool) -> None:
    for pack, pack_model in sorted(models.items()):
        upgrade_text = render_consolidated_upgrade_prototypes(pack_model)
        setup_text = render_dlc_general_setup_patch(pack_model, pack)
        weapon_text = render_weapon_sections_patch(pack_model, content_pack=pack)
        validate_rendered_outputs(pack_model, upgrade_text, setup_text)
        pack_root = output_root / pack
        write(pack_root / "UpgradePrototypes/UpgradePrototypes_patch_BPRUE.cfg", upgrade_text)
        write(pack_root / "WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg", setup_text)
        write(pack_root / "ItemPrototypes/ItemPrototypes_patch_BPRUE.cfg", weapon_text)
        if signature_effects:
            write(pack_root / "EffectPrototypes/EffectPrototypes_patch_BPRUE.cfg", render_dlc_signature_effects(pack))


def validate_rendered_outputs(model, upgrade_text, setup_text, npc_text=None):
    errors = []
    for upgrade in model.upgrades:
        if upgrade_text.count(f"{upgrade.sid} : struct.begin") != 1: errors.append(f"{upgrade.sid}: expected exactly one prototype definition")
        for setup_sid in upgrade.general_setup_sids:
            if setup_sid not in setup_text or upgrade.sid not in setup_text: errors.append(f"{upgrade.sid}: missing GeneralSetup registration for {setup_sid}")
        if npc_text is not None and upgrade.technician and upgrade.sid not in npc_text: errors.append(f"{upgrade.sid}: missing technician registration")
    if errors: raise ValueError("Generated upgrade output validation failed:\n  - " + "\n  - ".join(errors))


def render_vanilla_effect_ui_patch() -> str:
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// BPRUE UI compatibility patch for reused BaseGame upgrade effects.",
        "// Adds/overrides only UI metadata; gameplay values remain untouched.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for sid, localization_sid in VANILLA_EFFECT_LOCALIZATION_OVERRIDES.items():
        lines += [f"{sid} : struct.begin {{bpatch}}", f"   LocalizationSID = {localization_sid}", "   ShowUpgradeEffectValue = true", "   ShowUpgradeEffect = true", "struct.end", ""]
    for sid in VANILLA_TECHNICAL_EFFECTS_HIDDEN_FROM_UI:
        lines += [f"{sid} : struct.begin {{bpatch}}", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


def _float_scalar(block, name):
    raw = _direct_scalar(block, name)
    if raw is None: return None
    try: return float(raw)
    except ValueError: return None


def _section_index(block):
    if not block:
        raise ValueError("SectionSettings child is empty")
    header = block[0] if isinstance(block, list) else block
    match = re.search(r"\[(\d+)\]\s*:\s*struct\.begin", header)
    if not match:
        raise ValueError("SectionSettings child has no numeric index")
    return int(match.group(1))


def _blocks_by_sid(path):
    if not path.exists(): return {}
    return {_sid(block): block for block in _top_level_blocks(path.read_text(encoding="utf-8", errors="ignore")) if _sid(block)}


def _effective_scalar(sid, name, primary, fallback):
    seen = set(); current = sid
    while current and current not in seen:
        seen.add(current); block = primary.get(current) or fallback.get(current)
        if not block: return None
        value = _direct_scalar(block, name)
        if value is not None: return value
        current = _refkey(block)
    return None


def _effective_section_settings(sid, primary, fallback):
    seen = set(); current = sid
    while current and current not in seen:
        seen.add(current); block = primary.get(current) or fallback.get(current)
        if not block: return None
        settings = _direct_child(block, "SectionSettings")
        if settings is not None: return settings
        current = _refkey(block)
    return None


def _distance(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])

def _resolve_section_position(origin, occupied):
    if all(_distance(origin, point) >= MIN_SECTION_DISTANCE for point in occupied): return origin
    for ring in range(1, SECTION_NUDGE_RINGS + 1):
        radius = SECTION_NUDGE_STEP * ring
        for direction in range(SECTION_SEARCH_DIRECTIONS):
            angle = (2.0 * math.pi * direction) / SECTION_SEARCH_DIRECTIONS
            candidate = (origin[0] + math.cos(angle) * radius, origin[1] + math.sin(angle) * radius)
            if all(_distance(candidate, point) >= MIN_SECTION_DISTANCE for point in occupied): return candidate
    raise ValueError(f"Unable to place upgrade section near {origin} without collision")


def render_weapon_sections_patch(model, content_pack=None):
    wanted_setups = {setup for upgrade in model.upgrades for setup in upgrade.general_setup_sids}
    source_path = DLC_ROOT / content_pack / "ItemPrototypes.cfg" if content_pack else VANILLA_WEAPONS
    vanilla = _blocks_by_sid(VANILLA_WEAPONS)
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
            sections.append({"index": _section_index(section), "target": target, "enabled": (_direct_scalar(section, "SectionIsEnabled") or "").lower() == "true", "origin": (left, top)})
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
            if moved: lines += [f"         // BPRUE hotspot moved from ({entry['origin'][0]:.6f}, {entry['origin'][1]:.6f}) for UI spacing", f"         LeftPosition = {position[0]:.6f}", f"         TopPosition = {position[1]:.6f}"]
            lines.append("      struct.end")
        lines += ["   struct.end", "struct.end", ""]; patches.extend(lines)

    scope = f"DLCGameData/{content_pack}" if content_pack else "BaseGame"
    header = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", f"// Scope: {scope}", "// Enables inherited predefined weapon upgrade sections for BPRUE.", f"// Minimum hotspot center distance: {MIN_SECTION_DISTANCE:.1f}", f"// Search ring step: {SECTION_NUDGE_STEP:.1f}; directions per ring: {SECTION_SEARCH_DIRECTIONS}; rings: {SECTION_NUDGE_RINGS}", f"// Patched weapons: {weapon_count}; enabled disabled sections: {enabled_count}; repositioned collisions: {moved_count}", "// -----------------------------------------------------------------------------", ""]
    return "\n".join(header + patches).rstrip() + "\n"


def render_conversion_weapon_prototypes(model):
    """Render BPRUE-owned pistol-slot variants with the source weapon's BPRUE section overrides."""
    wanted_setups = {setup for upgrade in model.upgrades for setup in upgrade.general_setup_sids}
    vanilla = _blocks_by_sid(VANILLA_WEAPONS)
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// BPRUE pistol-slot conversion weapon prototypes.",
        "// Converted variants inherit BaseGame weapons and mirror BPRUE section overrides.",
        "// -----------------------------------------------------------------------------",
        "",
    ]

    for variant in PISTOL_CONVERSION_VARIANTS:
        weapon = vanilla.get(variant.source_weapon_sid)
        if not weapon:
            raise ValueError(f"No Vanilla weapon prototype found for conversion source {variant.source_weapon_sid}")

        setup_sid = _effective_scalar(variant.source_weapon_sid, "GeneralWeaponSetup", vanilla, {})
        settings = _effective_section_settings(variant.source_weapon_sid, vanilla, {})
        changed = []
        if setup_sid in wanted_setups and settings:
            sections = []
            for section in _indexed_children(settings):
                target = _direct_scalar(section, "UpgradeTargetPartType")
                left = _float_scalar(section, "LeftPosition")
                top = _float_scalar(section, "TopPosition")
                if target is None or left is None or top is None:
                    continue
                sections.append({
                    "index": _section_index(section),
                    "enabled": (_direct_scalar(section, "SectionIsEnabled") or "").lower() == "true",
                    "origin": (left, top),
                })

            occupied = [entry["origin"] for entry in sections if entry["enabled"]]
            for entry in sections:
                if entry["enabled"]:
                    continue
                position = _resolve_section_position(entry["origin"], occupied)
                occupied.append(position)
                changed.append((entry, position, position != entry["origin"]))

        lines += [
            f"// {variant.source_weapon_sid} variant used after the pistol-slot conversion.",
            f"{variant.weapon_sid} : struct.begin {{refurl=@BaseGame/ItemPrototypes/WeaponPrototypes.cfg;refkey={variant.source_weapon_sid}}}",
            f"   SID = {variant.weapon_sid}",
            f"   LocalizationSID = {variant.localization_sid}",
            "   ItemSlotType = EInventoryEquipmentSlot::Pistol",
        ]

        if changed:
            lines.append("   SectionSettings : struct.begin {bpatch}")
            for entry, position, moved in changed:
                lines += [
                    f"      [{entry['index']}] : struct.begin {{bpatch}}",
                    "         SectionIsEnabled = true",
                ]
                if moved:
                    lines += [
                        f"         // BPRUE hotspot moved from ({entry['origin'][0]:.6f}, {entry['origin'][1]:.6f}) for UI spacing",
                        f"         LeftPosition = {position[0]:.6f}",
                        f"         TopPosition = {position[1]:.6f}",
                    ]
                lines.append("      struct.end")
            lines.append("   struct.end")

        lines += ["struct.end", ""]

    return "\n".join(lines).rstrip() + "\n"


def write(path, content): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8"); print(f"Generated {path}")


def _remove_independent_dlc_output():
    root = CONTENT_ROOT / "GameLite/DLCGameData/BPRUpgradesExpanded"
    for relative in ("UpgradePrototypes/UpgradePrototypes.cfg", "WeaponData/WeaponGeneralSetupPrototypes.cfg", "ItemPrototypes/ItemPrototypes.cfg"):
        path = root / relative
        if path.exists(): path.unlink(); print(f"Removed experimental DLC output {path}")


def _remove_obsolete_bprue_effect_ui_patch():
    path = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_EffectUIOverrides.cfg"
    if path.exists():
        path.unlink()
        print(f"Removed obsolete mod-owned effect UI patch {path}")


def main():
    print("Building unified weapon upgrade model")
    model, configs = build_model(apply_layout=False); dlc_models = build_dlc_outputs(model, configs); edition_models = build_edition_outputs(model, configs); apply_layout_to_model(model); model.validate(); print(f"Built {model.summary()}")
    attachments = {sid: attachment_block(sid, data) for sid, data in CONVERSION_ATTACHMENTS.items()}
    upgrade_text = render_consolidated_upgrade_prototypes(model); setup_text = render_final_general_setup_patch(model, attachments); npc_text = render_technician_patch(model, dlc_models=dlc_models); weapon_text = render_weapon_sections_patch(model); conversion_weapon_text = render_conversion_weapon_prototypes(model)
    validate_rendered_outputs(model, upgrade_text, setup_text, npc_text)
    write(UPGRADES_PATH, upgrade_text); write(GENERAL_SETUP_PATH, setup_text); write(WEAPON_PATH, weapon_text); write(CONVERSION_WEAPON_PATH, conversion_weapon_text); write(NPC_PATH, npc_text); write(VANILLA_COMPACTION_PATH, render_vanilla_compaction_patch())
    write(VANILLA_EFFECT_UI_PATH, render_vanilla_effect_ui_patch()); _remove_obsolete_bprue_effect_ui_patch(); _remove_independent_dlc_output()
    _render_content_pack_outputs(dlc_models, DLC_OUTPUT_ROOT, signature_effects=True)
    _render_content_pack_outputs(edition_models, EDITIONS_OUTPUT_ROOT, signature_effects=False)
    write(ar.EFFECT_OUTPUT_PATH, ar.render_effect_patch(configs["ar"])); write(smg.EFFECT_OUTPUT_PATH, smg.render_effects()); write(shotgun.EFFECT_OUTPUT, shotgun.render_effects()); write(pistol.EFFECT_OUTPUT, pistol.render_effects()); write(sniper.EFFECT_OUTPUT, sniper.render_effects()); write(MACHINE_GUN_EFFECT_PATH, machine_gun.render_effects()); write(SHARED_EFFECT_PATH, render_shared_effects()); write(UNIQUE_SIGNATURE_EFFECT_PATH, render_unique_signature_effects())
    print(f"Validated and rendered {len(model.upgrades)} base/Unique upgrades plus {sum(len(m.upgrades) for m in dlc_models.values())} DLC upgrades plus {sum(len(m.upgrades) for m in edition_models.values())} Edition upgrades.")


if __name__ == "__main__": main()
