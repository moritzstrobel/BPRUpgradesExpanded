from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from upgrade_renderers import render_general_setup_patch, render_upgrade_prototypes

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "smg_upgrades.json"
UPGRADE_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_SMGUpgradePrototypes.cfg"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_SMGEffectPrototypes.cfg"
WEAPON_OUTPUT_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_SMGModules.cfg"
TEMPLATE_SID = "BPRUE_SMGModuleTemplate"

MODULES = {
    "quick_draw": ("Readiness_QuickDraw", "sid_bprue_smg_quick_draw_name", "sid_bprue_smg_quick_draw_description", 2200, "Top", "Body", ["AimingTimePos15Effect", "AimingMovementPos10Effect", "BPRUE_SMG_ReloadingTimePos10Effect"]),
    "stabilized": ("Readiness_Stabilized", "sid_bprue_smg_stabilized_name", "sid_bprue_smg_stabilized_description", 2400, "Top", "Body", ["RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]),
    "competition_reload": ("Reload_Competition", "sid_bprue_smg_competition_reload_name", "sid_bprue_smg_competition_reload_description", 2400, "Down", "Body", ["BPRUE_ReloadingTimeNeg20Effect", "AimingTimeNeg10Effect"]),
    "tactical_reload": ("Reload_Tactical", "sid_bprue_smg_tactical_reload_name", "sid_bprue_smg_tactical_reload_description", 2300, "Down", "Body", ["BPRUE_ReloadingTimeNeg10Effect", "AimingTimePos15Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "high_speed_action": ("Action_HighSpeed", "sid_bprue_smg_high_speed_action_name", "sid_bprue_smg_high_speed_action_description", 3000, "Top", "Barrel", ["BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect", "BPRUE_SMG_ReloadingTimePos10Effect"]),
    "controlled_action": ("Action_Controlled", "sid_bprue_smg_controlled_action_name", "sid_bprue_smg_controlled_action_description", 2800, "Top", "Barrel", ["BPRUE_FireIntervalPos5Effect", "RecoilPos15Effect", "ShotRecoveryPos20Effect", "BPRUE_ReloadingTimeNeg10Effect"]),
    "stock_lightweight": ("Stock_Lightweight", "sid_bprue_smg_stock_lightweight_name", "sid_bprue_smg_stock_lightweight_description", 2500, "Top", "Stock", ["AimingTimePos15Effect", "AimingMovementPos10Effect", "RecoilNeg15Effect"]),
    "stock_tactical": ("Stock_Tactical", "sid_bprue_smg_stock_tactical_name", "sid_bprue_smg_stock_tactical_description", 2700, "Down", "Stock", ["RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]),
    "stock_stabilized": ("Stock_Stabilized", "sid_bprue_smg_stock_stabilized_name", "sid_bprue_smg_stock_stabilized_description", 2900, None, "Stock", ["RecoilPos20Effect", "MaxDispersionPos15Effect", "BPRUE_Sniper_WeightPenalty10Effect"]),
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

CALIBER_STAT_EFFECTS = {
    ("A919", "A045"): ("BPRUE_SMG_DamagePos15Effect", "BPRUE_SMG_RecoilPenalty20Effect", "BPRUE_SMG_EffectiveRangePenalty10Effect"),
    ("A918", "A919"): ("BPRUE_SMG_DamagePos10Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_RecoilPenalty10Effect", "BPRUE_DurabilityPerShotNeg10Effect"),
    ("A045", "A919"): ("BPRUE_SMG_RecoilPos10Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_DamagePenalty10Effect"),
    ("A919", "A918"): ("BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_DurabilityPerShotPos10Effect", "BPRUE_SMG_DamagePenalty10Effect", "BPRUE_SMG_EffectiveRangePenalty10Effect"),
    ("A918", "A045"): ("BPRUE_SMG_DamagePos15Effect", "BPRUE_SMG_RecoilPenalty25Effect", "BPRUE_SMG_EffectiveRangePenalty15Effect"),
    ("A045", "A918"): ("BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_EffectiveRangePos15Effect", "BPRUE_SMG_DamagePenalty15Effect"),
}

IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/AK74/Barrel/Upgrade/T_AK47_Upg_a_1.T_AK47_Upg_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"
CALIBER_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_CaliberChange.T_PDA_Upgrades_Icon_CaliberChange'"
AMMO_ICON_ROOT = "/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Ammo"

def _ammo_icon(name: str) -> str:
    asset = f"T_Module_Ammo_{name}"
    return f"Texture2D'{AMMO_ICON_ROOT}/{asset}.{asset}'"

M10_A919_VARIANTS = {
    "Default": {
        "suffix": "A919",
        "text_sid": "sid_bprue_smg_caliber_a919_name",
        "hint_sid": "sid_bprue_smg_caliber_a919_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes919Effect",
        "stat_effects": ("BPRUE_SMG_RecoilPos10Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_DamagePenalty10Effect"),
        "icon": _ammo_icon("9x19"),
    },
    "AP": {
        "suffix": "A919_AP",
        "text_sid": "sid_bprue_smg_caliber_a919_ap_name",
        "hint_sid": "sid_bprue_smg_caliber_a919_ap_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes919APEffect",
        "stat_effects": ("BPRUE_SMG_ArmorPiercingPos15Effect", "BPRUE_SMG_RecoilPos10Effect", "BPRUE_SMG_EffectiveRangePos5Effect", "BPRUE_SMG_DamagePenalty15Effect"),
        "icon": _ammo_icon("9x19_ap"),
    },
}


M10_A918_VARIANTS = {
    "Default": {
        "suffix": "A918",
        "text_sid": "sid_bprue_smg_caliber_a918_name",
        "hint_sid": "sid_bprue_smg_caliber_a918_description",
        "ammo_effect": "ChangeAmmoTypes918Effect",
        "stat_effects": ("BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_EffectiveRangePos15Effect", "BPRUE_SMG_DamagePenalty15Effect"),
        "icon": _ammo_icon("9x18"),
    },
    "AP": {
        "suffix": "A918_AP",
        "text_sid": "sid_bprue_smg_caliber_a918_ap_name",
        "hint_sid": "sid_bprue_smg_caliber_a918_ap_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes918APEffect",
        "stat_effects": ("BPRUE_SMG_ArmorPiercingPos15Effect", "BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_DamagePenalty20Effect"),
        "icon": _ammo_icon("9x18_ap"),
    },
}


BUCKET_A919_VARIANTS = {
    "Default": {
        "suffix": "A919",
        "text_sid": "sid_bprue_smg_caliber_a919_name",
        "hint_sid": "sid_bprue_smg_caliber_a919_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes919Effect",
        "stat_effects": ("BPRUE_SMG_DamagePos10Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_RecoilPenalty10Effect", "BPRUE_DurabilityPerShotNeg10Effect"),
        "icon": _ammo_icon("9x19"),
    },
    "AP": {
        "suffix": "A919_AP",
        "text_sid": "sid_bprue_smg_caliber_a919_ap_name",
        "hint_sid": "sid_bprue_smg_caliber_a919_ap_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes919APEffect",
        "stat_effects": ("BPRUE_SMG_DamagePos5Effect", "BPRUE_SMG_ArmorPiercingPos15Effect", "BPRUE_SMG_EffectiveRangePos5Effect", "BPRUE_SMG_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg10Effect"),
        "icon": _ammo_icon("9x19_ap"),
    },
}

BUCKET_A045_VARIANTS = {
    "Default": {
        "suffix": "A045",
        "text_sid": "sid_bprue_smg_caliber_a045_name",
        "hint_sid": "sid_bprue_smg_caliber_a045_description",
        "ammo_effect": "ChangeAmmoTypes045Effect",
        "stat_effects": ("BPRUE_SMG_DamagePos15Effect", "BPRUE_SMG_RecoilPenalty25Effect", "BPRUE_SMG_EffectiveRangePenalty15Effect"),
        "icon": _ammo_icon("45acp"),
    },
    "AP": {
        "suffix": "A045_AP",
        "text_sid": "sid_bprue_smg_caliber_a045_ap_name",
        "hint_sid": "sid_bprue_smg_caliber_a045_ap_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes045APEffect",
        "stat_effects": ("BPRUE_SMG_DamagePos10Effect", "BPRUE_SMG_ArmorPiercingPos15Effect", "BPRUE_SMG_RecoilPenalty30Effect", "BPRUE_SMG_EffectiveRangePenalty15Effect"),
        "icon": _ammo_icon("45acp_ap"),
    },
    "Expanding": {
        "suffix": "A045_Expanding",
        "text_sid": "sid_bprue_smg_caliber_a045_expanding_name",
        "hint_sid": "sid_bprue_smg_caliber_a045_expanding_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes045ExpandingEffect",
        "stat_effects": ("BPRUE_SMG_DamagePos20Effect", "BPRUE_SMG_RecoilPenalty30Effect", "BPRUE_SMG_EffectiveRangePenalty20Effect"),
        "icon": _ammo_icon("45acp_hp"),
    },
}


ZUBR_A918_VARIANTS = {
    "Default": {
        "suffix": "A918",
        "text_sid": "sid_bprue_smg_caliber_a918_name",
        "hint_sid": "sid_bprue_smg_caliber_a918_description",
        "ammo_effect": "ChangeAmmoTypes918Effect",
        "stat_effects": ("BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_DurabilityPerShotPos10Effect", "BPRUE_SMG_DamagePenalty10Effect", "BPRUE_SMG_EffectiveRangePenalty10Effect"),
        "icon": _ammo_icon("9x18"),
    },
    "AP": {
        "suffix": "A918_AP",
        "text_sid": "sid_bprue_smg_caliber_a918_ap_name",
        "hint_sid": "sid_bprue_smg_caliber_a918_ap_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes918APEffect",
        "stat_effects": ("BPRUE_SMG_ArmorPiercingPos15Effect", "BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_DurabilityPerShotPos10Effect", "BPRUE_SMG_DamagePenalty15Effect", "BPRUE_SMG_EffectiveRangePenalty15Effect"),
        "icon": _ammo_icon("9x18_ap"),
    },
}

ZUBR_A045_VARIANTS = {
    "Default": {
        "suffix": "A045",
        "text_sid": "sid_bprue_smg_caliber_a045_name",
        "hint_sid": "sid_bprue_smg_caliber_a045_description",
        "ammo_effect": "ChangeAmmoTypes045Effect",
        "stat_effects": ("BPRUE_SMG_DamagePos15Effect", "BPRUE_SMG_RecoilPenalty20Effect", "BPRUE_SMG_EffectiveRangePenalty10Effect"),
        "icon": _ammo_icon("45acp"),
    },
    "AP": {
        "suffix": "A045_AP",
        "text_sid": "sid_bprue_smg_caliber_a045_ap_name",
        "hint_sid": "sid_bprue_smg_caliber_a045_ap_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes045APEffect",
        "stat_effects": ("BPRUE_SMG_DamagePos10Effect", "BPRUE_SMG_ArmorPiercingPos15Effect", "BPRUE_SMG_RecoilPenalty25Effect", "BPRUE_SMG_EffectiveRangePenalty10Effect"),
        "icon": _ammo_icon("45acp_ap"),
    },
    "Expanding": {
        "suffix": "A045_Expanding",
        "text_sid": "sid_bprue_smg_caliber_a045_expanding_name",
        "hint_sid": "sid_bprue_smg_caliber_a045_expanding_description",
        "ammo_effect": "BPRUE_SMG_ChangeAmmoTypes045ExpandingEffect",
        "stat_effects": ("BPRUE_SMG_DamagePos20Effect", "BPRUE_SMG_RecoilPenalty25Effect", "BPRUE_SMG_EffectiveRangePenalty15Effect"),
        "icon": _ammo_icon("45acp_hp"),
    },
}

def load_config() -> dict: return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
def sid(family: dict, key: str) -> str: return f"{family['prototype_prefix']}_Upgrade_BPRUE_{MODULES[key][0]}"
def caliber_sid(family: dict, caliber: str) -> str: return f"{family['prototype_prefix']}_Upgrade_BPRUE_Caliber_{caliber}"

def build_upgrades(config: dict) -> list[UpgradeDefinition]:
    upgrades=[]; families=config.get("families", {})
    if not families: raise ValueError("SMG config contains no families")
    for family in families.values():
        setup=family["general_setup_sid"]
        for group, keys in config["module_groups"].items():
            group_sids=[sid(family,key) for key in keys]
            for key in keys:
                _,text,hint,cost,vertical,target,effects=MODULES[key]; current=sid(family,key)
                upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=setup,weapon_class="SMG",group=group.title(),target_part=target,text_sid=text,hint_sid=hint,image=IMAGE,icon=ICON,cost=cost,effects=tuple(effects),blocking_sids=tuple(x for x in group_sids if x!=current),vertical_position=vertical,template_sid=TEMPLATE_SID))
    for family in config.get("caliber_families", {}).values():
        if not family.get("bprue_caliber_conversion", True): continue
        source_caliber=family["base_caliber"]; source_remove=CALIBER_DATA[source_caliber]["remove_ammo_effect"]
        conversion_sids=[]
        for caliber in family["conversions"]:
            variants = None
            if family["prototype_prefix"] == "GunM10" and caliber in ("A919", "A918"):
                variants = M10_A919_VARIANTS if caliber == "A919" else M10_A918_VARIANTS
            elif family["prototype_prefix"] == "GunBucket" and caliber in ("A919", "A045"):
                variants = BUCKET_A919_VARIANTS if caliber == "A919" else BUCKET_A045_VARIANTS
            elif family["prototype_prefix"] == "GunZubr" and caliber in ("A918", "A045"):
                variants = ZUBR_A918_VARIANTS if caliber == "A918" else ZUBR_A045_VARIANTS
            if variants:
                conversion_sids.extend(f"{family['prototype_prefix']}_Upgrade_BPRUE_Caliber_{spec['suffix']}" for spec in variants.values())
            else:
                conversion_sids.append(caliber_sid(family,caliber))
        for caliber in family["conversions"]:
            data=CALIBER_DATA[caliber]
            variants = None
            if family["prototype_prefix"] == "GunM10" and caliber in ("A919", "A918"):
                variants = M10_A919_VARIANTS if caliber == "A919" else M10_A918_VARIANTS
            elif family["prototype_prefix"] == "GunBucket" and caliber in ("A919", "A045"):
                variants = BUCKET_A919_VARIANTS if caliber == "A919" else BUCKET_A045_VARIANTS
            elif family["prototype_prefix"] == "GunZubr" and caliber in ("A918", "A045"):
                variants = ZUBR_A918_VARIANTS if caliber == "A918" else ZUBR_A045_VARIANTS
            if variants:
                for spec in variants.values():
                    current=f"{family['prototype_prefix']}_Upgrade_BPRUE_Caliber_{spec['suffix']}"
                    upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=family["general_setup_sid"],weapon_class="SMG",group="Caliber",target_part="Body",text_sid=spec["text_sid"],hint_sid=spec["hint_sid"],image=IMAGE,icon=spec["icon"],cost=data["cost"],effects=(data["change_effect"],source_remove,spec["ammo_effect"],*spec["stat_effects"]),blocking_sids=tuple(x for x in conversion_sids if x!=current),template_sid=TEMPLATE_SID))
                continue
            current=caliber_sid(family,caliber); stat_effects=CALIBER_STAT_EFFECTS.get((source_caliber, caliber), ())
            upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=family["general_setup_sid"],weapon_class="SMG",group="Caliber",target_part="Body",text_sid=data["name_sid"],hint_sid=data["hint_sid"],image=IMAGE,icon=CALIBER_ICON,cost=data["cost"],effects=(data["change_effect"],source_remove,data["add_ammo_effect"],*stat_effects),blocking_sids=tuple(x for x in conversion_sids if x!=current),template_sid=TEMPLATE_SID))
    for setup,(current,text,hint,cost) in PISTOL_CONVERSIONS.items():
        upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=setup,weapon_class="SMG",group="Conversion",target_part="Body",text_sid=text,hint_sid=hint,image=IMAGE,icon=CALIBER_ICON,cost=cost,template_sid=TEMPLATE_SID,require_effects=False,standalone=True))
    return upgrades

def render_effects() -> str:
    defs = [
        ("BPRUE_SMG_DamagePos15Effect", "WeaponDamage", "15%", "Positive", "bprue_damage"),
        ("BPRUE_SMG_DamagePos10Effect", "WeaponDamage", "10%", "Positive", "bprue_damage"),
        ("BPRUE_SMG_DamagePos5Effect", "WeaponDamage", "5%", "Positive", "bprue_damage"),
        ("BPRUE_SMG_DamagePos20Effect", "WeaponDamage", "20%", "Positive", "bprue_damage"),
        ("BPRUE_SMG_ArmorPiercingPos15Effect", "ArmorPiercing", "15%", "Positive", "bprue_armor_piercing"),
        ("BPRUE_SMG_DamagePenalty10Effect", "WeaponDamage", "-10%", "Negative", "bprue_damage"),
        ("BPRUE_SMG_DamagePenalty15Effect", "WeaponDamage", "-15%", "Negative", "bprue_damage"),
        ("BPRUE_SMG_DamagePenalty20Effect", "WeaponDamage", "-20%", "Negative", "bprue_damage"),
        ("BPRUE_SMG_RecoilPenalty30Effect", "Recoil", "-30%", "Negative", "bprue_recoil"),
        ("BPRUE_SMG_RecoilPenalty25Effect", "Recoil", "-25%", "Negative", "bprue_recoil"),
        ("BPRUE_SMG_RecoilPenalty20Effect", "Recoil", "-20%", "Negative", "bprue_recoil"),
        ("BPRUE_SMG_RecoilPenalty15Effect", "Recoil", "-15%", "Negative", "bprue_recoil"),
        ("BPRUE_SMG_RecoilPenalty10Effect", "Recoil", "-10%", "Negative", "bprue_recoil"),
        ("BPRUE_SMG_RecoilPos10Effect", "Recoil", "10%", "Positive", "bprue_recoil"),
        ("BPRUE_SMG_RecoilPos15Effect", "Recoil", "15%", "Positive", "bprue_recoil"),
        ("BPRUE_SMG_EffectiveRangePos5Effect", "EffectiveFireDistance", "5%", "Positive", "bprue_effective_range"),
        ("BPRUE_SMG_EffectiveRangePos10Effect", "EffectiveFireDistance", "10%", "Positive", "bprue_effective_range"),
        ("BPRUE_SMG_EffectiveRangePos15Effect", "EffectiveFireDistance", "15%", "Positive", "bprue_effective_range"),
        ("BPRUE_SMG_EffectiveRangePenalty10Effect", "EffectiveFireDistance", "-10%", "Negative", "bprue_effective_range"),
        ("BPRUE_SMG_EffectiveRangePenalty15Effect", "EffectiveFireDistance", "-15%", "Negative", "bprue_effective_range"),
        ("BPRUE_SMG_EffectiveRangePenalty20Effect", "EffectiveFireDistance", "-20%", "Negative", "bprue_effective_range"),
        ("BPRUE_SMG_DurabilityPerShotPos10Effect", "DurabilityPerShot", "-10%", "Positive", "bprue_weapon_wear"),
    ]
    lines=["// AUTO-GENERATED - Source: smg_upgrades.json", "", "BPRUE_SMG_ReloadingTimePos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}", "   SID = BPRUE_SMG_ReloadingTimePos10Effect", "   Text = Increase Reloading Time", "   Type = EEffectType::ReloadingTime", "   LocalizationSID = bprue_reload_speed", "   ValueMin = 10%", "   ValueMax = 10%", "   bIsPermanent = true", "   Positive = EBeneficial::Negative", "   ShowUpgradeEffectValue = true", "   ShowUpgradeEffect = true", "struct.end", ""]
    for effect_sid,effect_type,value,beneficial,loc in defs:
        lines += [f"{effect_sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}", f"   SID = {effect_sid}", f"   Type = EEffectType::{effect_type}", f"   LocalizationSID = {loc}", f"   ValueMin = {value}", f"   ValueMax = {value}", "   bIsPermanent = true", f"   Positive = EBeneficial::{beneficial}", "   ShowUpgradeEffectValue = true", "   ShowUpgradeEffect = true", "struct.end", ""]
    lines += ["BPRUE_SMG_ChangeAmmoTypes045APEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}", "   SID = BPRUE_SMG_ChangeAmmoTypes045APEffect", "   AmmoTypeProjectiles : struct.begin", "      [0] : struct.begin", "         AmmoType = EAmmoType::ArmorPiercing", "         ProjectilePrototypeSID = P045", "      struct.end", "   struct.end", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", "", "BPRUE_SMG_ChangeAmmoTypes045ExpandingEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}", "   SID = BPRUE_SMG_ChangeAmmoTypes045ExpandingEffect", "   AmmoTypeProjectiles : struct.begin", "      [0] : struct.begin", "         AmmoType = EAmmoType::Expanding", "         ProjectilePrototypeSID = P045", "      struct.end", "   struct.end", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", "", "BPRUE_SMG_ChangeAmmoTypes918APEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}", "   SID = BPRUE_SMG_ChangeAmmoTypes918APEffect", "   AmmoTypeProjectiles : struct.begin", "      [0] : struct.begin", "         AmmoType = EAmmoType::ArmorPiercing", "         ProjectilePrototypeSID = P918", "      struct.end", "   struct.end", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", "", "BPRUE_SMG_ChangeAmmoTypes919APEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}", "   SID = BPRUE_SMG_ChangeAmmoTypes919APEffect", "   AmmoTypeProjectiles : struct.begin", "      [0] : struct.begin", "         AmmoType = EAmmoType::ArmorPiercing", "         ProjectilePrototypeSID = P919", "      struct.end", "   struct.end", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", "", "BPRUE_SMG_ChangeAmmoTypes919Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}", "   SID = BPRUE_SMG_ChangeAmmoTypes919Effect", "   AmmoTypeProjectiles : struct.begin", "      [0] : struct.begin", "         AmmoType = EAmmoType::Default", "         ProjectilePrototypeSID = P919", "      struct.end", "      [1] : struct.begin", "         AmmoType = EAmmoType::ArmorPiercing", "         ProjectilePrototypeSID = P919", "      struct.end", "   struct.end", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", "", "BPRUE_SMG_ChangeAmmoTypesNo918Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}", "   SID = BPRUE_SMG_ChangeAmmoTypesNo918Effect", "   AmmoTypeProjectiles : struct.begin", "      [0] : struct.begin", "         AmmoType = EAmmoType::Default", "         ProjectilePrototypeSID = P918", "      struct.end", "      [1] : struct.begin", "         AmmoType = EAmmoType::ArmorPiercing", "         ProjectilePrototypeSID = P918", "      struct.end", "   struct.end", "   Positive = EBeneficial::Negative", "   ShowUpgradeEffectValue = false", "   ShowUpgradeEffect = false", "struct.end", "", "BPRUE_VIPER_TEST : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}", "   SID = BPRUE_VIPER_TEST", "   Type = EEffectType::CameraShake", "   Positive = EBeneficial::Negative", "   CameraShakeEffectSubtype = ECameraShakeEffectSubtype::AddEffect", "   CameraShakePrototypeSID = BPR_PM_WeaponConversion_Shake", "struct.end", ""]
    return "\n".join(lines)

def main():
    config=load_config(); model=UpgradeBuildModel(); model.extend(build_upgrades(config)); model.validate()
    outputs={UPGRADE_OUTPUT_PATH:render_upgrade_prototypes(model,source="smg_upgrades.json",template_sid=TEMPLATE_SID),EFFECT_OUTPUT_PATH:render_effects(),WEAPON_OUTPUT_PATH:render_general_setup_patch(model)}
    for path,content in outputs.items(): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding="utf-8"); print(f"Generated {path}")
if __name__ == "__main__": main()
