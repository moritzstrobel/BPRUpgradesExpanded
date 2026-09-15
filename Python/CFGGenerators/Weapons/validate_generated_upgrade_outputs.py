from __future__ import annotations

from pathlib import Path

import generate_assault_rifle_upgrades as ar
import generate_pistol_upgrades as pistol
import generate_shotgun_upgrades as shotgun
import generate_smg_upgrades as smg
import generate_sniper_upgrades as sniper
from upgrade_build_model import UpgradeBuildModel

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
UPGRADES_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
GENERAL_SETUP_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
NPC_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"


def build_complete_model() -> UpgradeBuildModel:
    model = UpgradeBuildModel()
    model.extend(ar.build_upgrades(ar.load_config()))
    model.extend(smg.build_upgrades(smg.load_config()))
    model.extend(shotgun.build_upgrades(shotgun.cfg()))
    model.extend(pistol.build_upgrades(pistol.load_config()))
    model.extend(sniper.build_upgrades(sniper.load_config()))
    model.validate()
    return model


def main() -> None:
    model = build_complete_model()
    upgrade_text = UPGRADES_PATH.read_text(encoding="utf-8")
    setup_text = GENERAL_SETUP_PATH.read_text(encoding="utf-8")
    npc_text = NPC_PATH.read_text(encoding="utf-8")
    errors: list[str] = []

    for upgrade in model.upgrades:
        definition = f"{upgrade.sid} : struct.begin"
        count = upgrade_text.count(definition)
        if count != 1:
            errors.append(f"{upgrade.sid}: expected exactly one prototype definition, found {count}")
        for setup_sid in upgrade.general_setup_sids:
            if setup_sid not in setup_text or upgrade.sid not in setup_text:
                errors.append(f"{upgrade.sid}: missing GeneralSetup registration for {setup_sid}")
        if upgrade.technician and upgrade.sid not in npc_text:
            errors.append(f"{upgrade.sid}: missing technician registration")

    if errors:
        raise ValueError("Generated upgrade output validation failed:\n  - " + "\n  - ".join(errors))

    print(f"Validated {len(model.upgrades)} generated upgrades across prototypes, GeneralSetup and technicians.")


if __name__ == "__main__":
    main()
