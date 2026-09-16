from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CFG_ROOT = SCRIPT_DIR.parent
PYTHON_ROOT = CFG_ROOT.parent
CONTENT_ROOT = PYTHON_ROOT.parent
CLASS_DIRS = {
    "ar": CFG_ROOT / "AssaultRifles",
    "smg": CFG_ROOT / "SMGs",
    "shotgun": CFG_ROOT / "Shotguns",
    "pistol": CFG_ROOT / "Pistols",
    "sniper": CFG_ROOT / "Snipers",
}
for path in (SCRIPT_DIR, *CLASS_DIRS.values()):
    sys.path.insert(0, str(path))

import generate_assault_rifle_upgrades as ar
import generate_pistol_upgrades as pistol
import generate_shotgun_upgrades as shotgun
import generate_smg_upgrades as smg
import generate_sniper_upgrades as sniper
from apply_module_layout import apply_layout_to_model
from specialization_modules import build_shared_specializations, render_shared_effects
from upgrade_build_model import UpgradeBuildModel
from upgrade_renderers import render_consolidated_upgrade_prototypes, render_final_general_setup_patch, render_technician_patch

UPGRADE_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_SharedSpecializationUpgradePrototypes.cfg"
EFFECT_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_SharedSpecializationEffectPrototypes.cfg"
SETUP_OUTPUT = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_SharedSpecializations.cfg"
NPC_OUTPUT = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE_SharedSpecializations.cfg"


def build_model() -> UpgradeBuildModel:
    configs = {
        "ar": ar.load_config(),
        "smg": smg.load_config(),
        "shotgun": shotgun.cfg(),
        "pistol": pistol.load_config(),
        "sniper": sniper.load_config(),
    }
    model = UpgradeBuildModel()
    model.extend(build_shared_specializations(
        families=configs["pistol"]["families"], class_key="pistol", weapon_class="Pistol",
        template_sid=pistol.TEMPLATE_SID, image_for_family=lambda _: pistol.IMAGE, icon=pistol.ICON, sid_namespace="PistolShared"))
    model.extend(build_shared_specializations(
        families=configs["smg"]["families"], class_key="smg", weapon_class="SMG",
        template_sid=smg.TEMPLATE_SID, image_for_family=lambda _: smg.IMAGE, icon=smg.ICON, sid_namespace="SMGShared"))
    model.extend(build_shared_specializations(
        families=configs["ar"]["families"], class_key="assault_rifle", weapon_class="AR",
        template_sid=ar.MODULE_TEMPLATE_SID, image_for_family=lambda family: family["image"], icon=ar.DEFAULT_ICON, sid_namespace="ARShared"))
    model.extend(build_shared_specializations(
        families=configs["shotgun"]["families"], class_key="shotgun", weapon_class="SG",
        template_sid=shotgun.TEMPLATE_SID, image_for_family=lambda _: shotgun.IMAGE, icon=shotgun.ICON, sid_namespace="SGShared"))
    model.extend(build_shared_specializations(
        families=configs["sniper"]["families"], class_key="sniper", weapon_class="Sniper",
        template_sid=sniper.TEMPLATE_SID, image_for_family=lambda _: sniper.IMAGE, icon=sniper.ICON, sid_namespace="SniperShared"))
    model.validate()
    apply_layout_to_model(model)
    model.validate()
    return model


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Generated {path}")


def main() -> None:
    model = build_model()
    write(UPGRADE_OUTPUT, render_consolidated_upgrade_prototypes(model))
    write(EFFECT_OUTPUT, render_shared_effects())
    write(SETUP_OUTPUT, render_final_general_setup_patch(model, {}))
    write(NPC_OUTPUT, render_technician_patch(model))
    print(f"Generated shared specialization modules from {model.summary()}")


if __name__ == "__main__":
    main()
