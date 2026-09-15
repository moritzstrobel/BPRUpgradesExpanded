from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "smg_upgrades.json"
UPGRADE_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "ModGameData" / "BPRUpgradesExpanded" / "UpgradePrototypes" / "BPRUE_SMGUpgradePrototypes.cfg"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "ModGameData" / "BPRUpgradesExpanded" / "EffectPrototypes" / "BPRUE_SMGEffectPrototypes.cfg"
WEAPON_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "WeaponData" / "WeaponGeneralSetupPrototypes" / "WeaponGeneralSetupPrototypes_patch_BPRUE_SMGModules.cfg"

MODULES = {
    "quick_draw": ("Readiness_QuickDraw", "sid_bprue_smg_quick_draw_name", "sid_bprue_smg_quick_draw_description", 2200, "Top", "Body", ["AimingTimePos15Effect", "AimingMovementPos10Effect", "BPRUE_SMG_ReloadingTimePos10Effect"]),
    "stabilized": ("Readiness_Stabilized", "sid_bprue_smg_stabilized_name", "sid_bprue_smg_stabilized_description", 2400, "Top", "Body", ["RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]),
    "competition_reload": ("Reload_Competition", "sid_bprue_smg_competition_reload_name", "sid_bprue_smg_competition_reload_description", 2400, "Down", "Body", ["BPRUE_ReloadingTimeNeg20Effect", "AimingTimeNeg10Effect"]),
    "tactical_reload": ("Reload_Tactical", "sid_bprue_smg_tactical_reload_name", "sid_bprue_smg_tactical_reload_description", 2300, "Down", "Body", ["BPRUE_ReloadingTimeNeg10Effect", "AimingTimePos15Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "high_speed_action": ("Action_HighSpeed", "sid_bprue_smg_high_speed_action_name", "sid_bprue_smg_high_speed_action_description", 3000, "Top", "Barrel", ["BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect", "BPRUE_SMG_ReloadingTimePos10Effect"]),
    "controlled_action": ("Action_Controlled", "sid_bprue_smg_controlled_action_name", "sid_bprue_smg_controlled_action_description", 2800, "Top", "Barrel", ["BPRUE_FireIntervalPos5Effect", "RecoilPos15Effect", "ShotRecoveryPos20Effect", "BPRUE_ReloadingTimeNeg10Effect"]),
}

PISTOL_CONVERSIONS = {
    "GunViper_PP": ("GunViper_Upgrade_BPRUE_PistolConversion", "sid_bprue_viper_pistol_conversion_name", "sid_bprue_viper_pistol_conversion_description", 2500),
    "GunAKU_PP": ("GunAKU_Upgrade_BPRUE_PistolConversion", "sid_bprue_smg_pistol_conversion_name", "sid_bprue_smg_pistol_conversion_description", 2500),
    "GunBucket_PP": ("GunBucket_Upgrade_BPRUE_PistolConversion", "sid_bprue_smg_pistol_conversion_name", "sid_bprue_smg_pistol_conversion_description", 3000),
    "GunIntegral_PP": ("GunIntegral_Upgrade_BPRUE_PistolConversion", "sid_bprue_smg_pistol_conversion_name", "sid_bprue_smg_pistol_conversion_description", 3500),
    "GunZubr_PP": ("GunZubr_Upgrade_BPRUE_PistolConversion", "sid_bprue_smg_pistol_conversion_name", "sid_bprue_smg_pistol_conversion_description", 4000),
    "GunFora230_PP_GS": ("GunFora230_Upgrade_BPRUE_PistolConversion", "sid_bprue_smg_pistol_conversion_name", "sid_bprue_smg_pistol_conversion_description", 3000),
}

CALIBER_DATA = {
    "A918": {"name_sid": "sid_bprue_smg_caliber_a918_name", "hint_sid": "sid_bprue_smg_caliber_a918_description", "change_effect": "ChangeCaliber918Effect", "add_ammo_effect": "ChangeAmmoTypes918Effect", "remove_ammo_effect": "BPRUE_SMG_ChangeAmmoTypesNo918Effect", "cost": 2400},
    "A919": {"name_sid": "sid_bprue_smg_caliber_a919_name", "hint_sid": "sid_bprue_smg_caliber_a919_description", "change_effect": "ChangeCaliber919Effect", "add_ammo_effect": "BPRUE_SMG_ChangeAmmoTypes919Effect", "remove_ammo_effect": "ChangeAmmoTypesNo919Effect", "cost": 2600},
    "A045": {"name_sid": "sid_bprue_smg_caliber_a045_name", "hint_sid": "sid_bprue_smg_caliber_a045_description", "change_effect": "ChangeCaliber045Effect", "add_ammo_effect": "ChangeAmmoTypes045Effect", "remove_ammo_effect": "ChangeAmmoTypesNo045Effect", "cost": 3000},
}

IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/AK74/Barrel/Upgrade/T_AK47_Upg_a_1.T_AK47_Upg_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"
CALIBER_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_CaliberChange.T_PDA_Upgrades_Icon_CaliberChange'"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def sid(key):
    return f"BPRUE_SMG_Upgrade_{MODULES[key][0]}"


def caliber_sid(family: dict, caliber: str) -> str:
    return f"{family['prototype_prefix']}_Upgrade_BPRUE_Caliber_{caliber}"


def array(name, values):
    return [f"   {name} : struct.begin", *[f"      [{i}] = {v}" for i, v in enumerate(values)], "   struct.end"]


def render_upgrades(config):
    lines = [
        "// AUTO-GENERATED - Source: smg_upgrades.json",
        "",
        "BPRUE_SMGModuleTemplate : struct.begin {refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}",
        "   SID = BPRUE_SMGModuleTemplate",
        "   IsModification = true",
        "struct.end",
        "",
    ]

    for group, keys in config["module_groups"].items():
        group_sids = [sid(k) for k in keys]
        for key in keys:
            suffix, text, hint, cost, vertical, target, effects = MODULES[key]
            current = sid(key)
            lines += [
                f"{current} : struct.begin {{refkey=BPRUE_SMGModuleTemplate}}",
                f"   SID = {current}", f"   Text = {text}", f"   Hint = {hint}",
                f"   Image = {IMAGE}", f"   Icon = {ICON}", f"   BaseCost = {cost}",
                f"   VerticalPosition = EUpgradeVerticalPosition::{vertical}",
                f"   UpgradeTargetPart = EUpgradeTargetPartType::{target}",
            ]
            lines += array("EffectPrototypeSIDs", effects)
            lines += array("BlockingUpgradePrototypeSIDs", [x for x in group_sids if x != current])
            lines += ["struct.end", ""]

    for family in config.get("caliber_families", {}).values():
        conversion_sids = [caliber_sid(family, caliber) for caliber in family["conversions"]]
        source_remove_effect = CALIBER_DATA[family["base_caliber"]]["remove_ammo_effect"]
        for caliber in family["conversions"]:
            data = CALIBER_DATA[caliber]
            current = caliber_sid(family, caliber)
            lines += [
                f"{current} : struct.begin {{refkey=BPRUE_SMGModuleTemplate}}",
                f"   SID = {current}", f"   Text = {data['name_sid']}", f"   Hint = {data['hint_sid']}",
                f"   Image = {IMAGE}", f"   Icon = {CALIBER_ICON}", f"   BaseCost = {data['cost']}",
                "   VerticalPosition = EUpgradeVerticalPosition::Top",
                "   UpgradeTargetPart = EUpgradeTargetPartType::Body",
            ]
            lines += array("EffectPrototypeSIDs", [data["change_effect"], source_remove_effect, data["add_ammo_effect"]])
            lines += array("BlockingUpgradePrototypeSIDs", [x for x in conversion_sids if x != current])
            lines += ["struct.end", ""]

    # Pistol-conversion upgrades used to be a checked-in split CFG that the
    # merger tried to preserve between runs. Generate them here instead so they
    # pass through the same layout step as every other SMG specialization.
    lines += [
        "// --- SMG pistol-conversion modules --------------------------------------",
        "",
        "BPRUE_SMGConversionUpgradeTemplate : struct.begin {refkey=BPRUE_SMGModuleTemplate}",
        "   SID = BPRUE_SMGConversionUpgradeTemplate",
        "struct.end",
        "",
    ]
    for _, (current, text, hint, cost) in PISTOL_CONVERSIONS.items():
        lines += [
            f"{current} : struct.begin {{refkey=BPRUE_SMGConversionUpgradeTemplate}}",
            f"   SID = {current}", f"   Text = {text}", f"   Hint = {hint}",
            f"   Image = {IMAGE}", f"   Icon = {CALIBER_ICON}", f"   BaseCost = {cost}",
            "   VerticalPosition = EUpgradeVerticalPosition::Down",
            "   UpgradeTargetPart = EUpgradeTargetPartType::Body",
            "struct.end", "",
        ]

    return "\n".join(lines)


def render_effects():
    return """// AUTO-GENERATED - Source: smg_upgrades.json

BPRUE_SMG_ReloadingTimePos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SMG_ReloadingTimePos10Effect
   Text = Increase Reloading Time
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_SMG_ChangeAmmoTypes919Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_SMG_ChangeAmmoTypes919Effect
   AmmoTypeProjectiles : struct.begin
      [0] : struct.begin
         AmmoType = EAmmoType::Default
         ProjectilePrototypeSID = P919
      struct.end
      [1] : struct.begin
         AmmoType = EAmmoType::ArmorPiercing
         ProjectilePrototypeSID = P919
      struct.end
   struct.end
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_SMG_ChangeAmmoTypesNo918Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_SMG_ChangeAmmoTypesNo918Effect
   AmmoTypeProjectiles : struct.begin
      [0] : struct.begin
         AmmoType = EAmmoType::Default
         ProjectilePrototypeSID = P918
      struct.end
      [1] : struct.begin
         AmmoType = EAmmoType::ArmorPiercing
         ProjectilePrototypeSID = P918
      struct.end
   struct.end
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_VIPER_TEST : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_VIPER_TEST
   Type = EEffectType::CameraShake
   Positive = EBeneficial::Negative
   CameraShakeEffectSubtype = ECameraShakeEffectSubtype::AddEffect
   CameraShakePrototypeSID = BPR_PM_WeaponConversion_Shake
struct.end
"""


def render_weapons(config):
    module_sids = [sid(key) for keys in config["module_groups"].values() for key in keys]
    by_general_setup: dict[str, list[str]] = {}
    for family in config["families"].values():
        by_general_setup.setdefault(family["general_setup_sid"], []).extend(module_sids)
    for family in config.get("caliber_families", {}).values():
        target = by_general_setup.setdefault(family["general_setup_sid"], [])
        target.extend(caliber_sid(family, caliber) for caliber in family["conversions"])
    for general_setup_sid, (conversion_sid, _, _, _) in PISTOL_CONVERSIONS.items():
        by_general_setup.setdefault(general_setup_sid, []).append(conversion_sid)

    lines = [
        "// AUTO-GENERATED - Source: smg_upgrades.json", "",
        "// Shared specialization modules, caliber conversions and pistol-conversion upgrades.",
        "// This file is the single owner of UpgradePrototypeSIDs for these SMGs.", "",
    ]
    for general_setup_sid, upgrade_sids in by_general_setup.items():
        unique_sids = list(dict.fromkeys(upgrade_sids))
        lines += [
            f"{general_setup_sid} : struct.begin {{bpatch}}",
            "   UpgradePrototypeSIDs : struct.begin {bpatch}",
            *[f"      [*] = {x}" for x in unique_sids],
            "   struct.end", "struct.end", "",
        ]
    return "\n".join(lines)


def main():
    config = load_config()
    for path, content in {UPGRADE_OUTPUT_PATH: render_upgrades(config), EFFECT_OUTPUT_PATH: render_effects(), WEAPON_OUTPUT_PATH: render_weapons(config)}.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
