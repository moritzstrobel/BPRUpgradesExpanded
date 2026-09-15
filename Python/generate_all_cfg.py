from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WEAPONS_DIR = SCRIPT_DIR / "CFGGenerators" / "Weapons"
sys.path.insert(0, str(WEAPONS_DIR))

import generate_assault_rifle_upgrades as ar
import generate_pistol_upgrades as pistol
import generate_shotgun_upgrades as shotgun
import generate_smg_upgrades as smg
import generate_sniper_upgrades as sniper
from apply_module_layout import apply_layout_to_model
from smg_conversion_attachments import CONVERSION_ATTACHMENTS, attachment_block
from upgrade_build_model import UpgradeBuildModel
from upgrade_renderers import render_consolidated_upgrade_prototypes, render_final_general_setup_patch

CONTENT_ROOT = SCRIPT_DIR.parent
UPGRADES_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
GENERAL_SETUP_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
NPC_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"


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
    npc_text = ar.render_npc_patch(configs["ar"], model)
    validate_rendered_outputs(model, upgrade_text, setup_text, npc_text)

    write(UPGRADES_PATH, upgrade_text)
    write(GENERAL_SETUP_PATH, setup_text)
    write(NPC_PATH, npc_text)
    write(ar.EFFECT_OUTPUT_PATH, ar.render_effect_patch(configs["ar"]))
    write(smg.EFFECT_OUTPUT_PATH, smg.render_effects())
    write(shotgun.EFFECT_OUTPUT, shotgun.render_effects())
    write(pistol.EFFECT_OUTPUT, pistol.render_effects())
    write(sniper.EFFECT_OUTPUT, sniper.render_effects())
    print(f"Validated and rendered {len(model.upgrades)} upgrades in one build pass.")


if __name__ == "__main__":
    main()
