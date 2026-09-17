from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "assault_rifles_upgrades.json"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_EffectPrototypes.cfg"
MODULE_TEMPLATE_SID = "BPRUE_ModuleTemplate"

POWER_CALIBER = {
    "A545": ("A762Sniper", "762", "sid_bprue_caliber_762_eastern_name", "sid_bprue_caliber_762_eastern_description", 2800),
    "A556": ("A762NATO", "762NATO", "sid_bprue_caliber_762_nato_name", "sid_bprue_caliber_762_nato_description", 3200),
}
CALIBER_EFFECTS = {
    "A762Sniper": ("ChangeCaliber762Effect", ("ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762NATOEffect", "ChangeAmmoTypesNo939Effect"), "ChangeAmmoTypes762Effect", ("BPRUE_DamagePos15Effect", "BPRUE_ArmorPiercingPos15Effect", "BPRUE_RecoilPenalty25Effect", "BPRUE_DurabilityPerShotNeg20Effect")),
    "A762NATO": ("BPRUE_ChangeCaliber762NATOEffect", ("ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"), "BPRUE_ChangeAmmoTypes762NATOEffect", ("BPRUE_DamagePos10Effect", "BPRUE_ArmorPiercingPos15Effect", "BPRUE_RecoilPenalty20Effect", "BPRUE_DurabilityPerShotNeg15Effect")),
}
DEFAULT_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"
CALIBER_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_CaliberChange.T_PDA_Upgrades_Icon_CaliberChange'"

MODULE_SPECS = {
    ("fire_control", "burst"): ("FireControl", "Burst", "Body", 3000, "sid_bprue_fire_control_burst_name", "sid_bprue_fire_control_burst_description", ("BPRUE_AddBurstFireModeEffect", "RecoilPos5Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    ("fire_control", "precision"): ("FireControl", "Precision", "Body", 3600, "sid_bprue_fire_control_precision_name", "sid_bprue_fire_control_precision_description", ("BPRUE_SemiAutoOnlyEffect", "BPRUE_DamagePos10Effect", "ArmorPiercingPos15Effect", "BPRUE_DurabilityPerShotNeg20Effect")),
    ("fire_rate", "high_speed"): ("FireRate", "HighSpeed", "Barrel", 3400, "sid_bprue_fire_rate_high_speed_name", "sid_bprue_fire_rate_high_speed_description", ("BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect")),
    ("fire_rate", "balanced"): ("FireRate", "Balanced", "Barrel", 3200, "sid_bprue_fire_rate_balanced_name", "sid_bprue_fire_rate_balanced_description", ("BPRUE_FireIntervalNeg10Effect", "RecoilPos10Effect", "ShotRecoveryPos20Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    ("reload", "competition"): ("Reload", "Competition", "Body", 2800, "sid_bprue_reload_competition_name", "sid_bprue_reload_competition_description", ("BPRUE_ReloadingTimeNeg20Effect", "RecoilNeg15Effect")),
    ("reload", "reinforced"): ("Reload", "Reinforced", "Body", 3000, "sid_bprue_reload_reinforced_name", "sid_bprue_reload_reinforced_description", ("BPRUE_ReloadingTimeNeg10Effect", "DurabilityPerShotPos20Effect", "BPRUE_FireIntervalPos5Effect")),
    ("stock", "lightweight"): ("Stock", "Lightweight", "Stock", 3000, "sid_bprue_stock_lightweight_name", "sid_bprue_stock_lightweight_description", ("AimingTimePos15Effect", "AimingMovementPos10Effect", "RecoilNeg15Effect")),
    ("stock", "stabilized"): ("Stock", "Stabilized", "Stock", 3200, "sid_bprue_stock_stabilized_name", "sid_bprue_stock_stabilized_description", ("RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect")),
    ("stock", "marksman"): ("Stock", "Marksman", "Stock", 3400, "sid_bprue_stock_marksman_name", "sid_bprue_stock_marksman_description", ("IdleSwayXPos20Effect", "IdleSwayYPos20Effect", "MaxDispersionPos15Effect", "AimingTimeNeg15Effect")),
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _definition(family: dict, group: str, variant: str, target: str, cost: int, text: str, hint: str, effects: tuple[str, ...], icon: str = DEFAULT_ICON) -> UpgradeDefinition:
    return UpgradeDefinition(sid=f"{family['prototype_prefix']}_Upgrade_BPRUE_{group}_{variant}", general_setup_sid=family["general_setup_sid"], weapon_class="AR", group=group, target_part=target, text_sid=text, hint_sid=hint, image=family["image"], icon=icon, cost=cost, effects=effects, template_sid=MODULE_TEMPLATE_SID)


def build_upgrades(config: dict) -> list[UpgradeDefinition]:
    result: list[UpgradeDefinition] = []
    for family in config["families"].values():
        family_upgrades: list[UpgradeDefinition] = []
        power = POWER_CALIBER.get(family["base_caliber"]) if family.get("bprue_caliber_conversion", True) else None
        if power:
            caliber, suffix, text, hint, cost = power
            change, removes, add, stat_effects = CALIBER_EFFECTS[caliber]
            family_upgrades.append(_definition(family, "Caliber", suffix, "Body", cost, text, hint, (change, *removes, add, *stat_effects), CALIBER_ICON))
        for group, variants in config["module_groups"].items():
            for variant in variants:
                family_upgrades.append(_definition(family, *MODULE_SPECS[(group, variant)]))
        by_group: dict[str, list[UpgradeDefinition]] = {}
        for upgrade in family_upgrades: by_group.setdefault(upgrade.group, []).append(upgrade)
        for upgrade in family_upgrades:
            siblings = tuple(item.sid for item in by_group[upgrade.group] if item.sid != upgrade.sid)
            result.append(UpgradeDefinition(**{**upgrade.__dict__, "blocking_sids": siblings}))
    return result


def configure_general_setups(config: dict, model: UpgradeBuildModel) -> None:
    for family in config["families"].values(): model.configure_general_setup(family["general_setup_sid"], FireQueueCount=3)


def render_effect_patch(config: dict) -> str: return _EFFECTS

_EFFECTS = r'''// AUTO-GENERATED - BPRUE assault-rifle shared effects

BPRUE_FireIntervalNeg10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_FireIntervalNeg10Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = -10%
   ValueMax = -10%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_FireIntervalNeg20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_FireIntervalNeg20Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = -20%
   ValueMax = -20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_FireIntervalPos5Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_FireIntervalPos5Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = 5%
   ValueMax = 5%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DamagePos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DamageTemplate}
   SID = BPRUE_DamagePos10Effect
   LocalizationSID = bprue_damage
   ValueMin = 10%
   ValueMax = 10%
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DamagePos15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DamageTemplate}
   SID = BPRUE_DamagePos15Effect
   LocalizationSID = bprue_damage
   ValueMin = 15%
   ValueMax = 15%
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_ArmorPiercingPos15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_ArmorPiercingPos15Effect
   Type = EEffectType::ArmorPiercing
   LocalizationSID = bprue_armor_piercing
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_RecoilPenalty20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=RecoilTemplate}
   SID = BPRUE_RecoilPenalty20Effect
   LocalizationSID = bprue_recoil
   ValueMin = -20%
   ValueMax = -20%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_RecoilPenalty25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=RecoilTemplate}
   SID = BPRUE_RecoilPenalty25Effect
   LocalizationSID = bprue_recoil
   ValueMin = -25%
   ValueMax = -25%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_DurabilityPerShotNeg10Effect
   LocalizationSID = bprue_weapon_wear
   ValueMin = 10%
   ValueMax = 10%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_DurabilityPerShotNeg15Effect
   LocalizationSID = bprue_weapon_wear
   ValueMin = 15%
   ValueMax = 15%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_DurabilityPerShotNeg20Effect
   LocalizationSID = bprue_weapon_wear
   ValueMin = 20%
   ValueMax = 20%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_ReloadingTimeNeg20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_ReloadingTimeNeg20Effect
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = -20%
   ValueMax = -20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_ReloadingTimeNeg10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_ReloadingTimeNeg10Effect
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = -10%
   ValueMax = -10%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_ChangeCaliber762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeCaliberTemplate}
   SID = BPRUE_ChangeCaliber762NATOEffect
   Caliber = EAmmoCaliber::A762NATO
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_ChangeAmmoTypes762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_ChangeAmmoTypes762NATOEffect
   AmmoTypeProjectiles : struct.begin
      [0] : struct.begin
         AmmoType = EAmmoType::Default
         ProjectilePrototypeSID = P762NATO
      struct.end
      [1] : struct.begin
         AmmoType = EAmmoType::ArmorPiercing
         ProjectilePrototypeSID = P762NATO
      struct.end
      [2] : struct.begin
         AmmoType = EAmmoType::Supersonic
         ProjectilePrototypeSID = P762NATO
      struct.end
   struct.end
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_ChangeAmmoTypesNo762Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_ChangeAmmoTypesNo762Effect
   AmmoTypeProjectiles : struct.begin
      [0] : struct.begin
         AmmoType = EAmmoType::Default
         ProjectilePrototypeSID = P762Sniper
      struct.end
      [1] : struct.begin
         AmmoType = EAmmoType::ArmorPiercing
         ProjectilePrototypeSID = P762Sniper
      struct.end
      [2] : struct.begin
         AmmoType = EAmmoType::Supersonic
         ProjectilePrototypeSID = P762Sniper
      struct.end
   struct.end
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_ChangeAmmoTypesNo762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_ChangeAmmoTypesNo762NATOEffect
   AmmoTypeProjectiles : struct.begin
      [0] : struct.begin
         AmmoType = EAmmoType::Default
         ProjectilePrototypeSID = P762NATO
      struct.end
      [1] : struct.begin
         AmmoType = EAmmoType::ArmorPiercing
         ProjectilePrototypeSID = P762NATO
      struct.end
      [2] : struct.begin
         AmmoType = EAmmoType::Supersonic
         ProjectilePrototypeSID = P762NATO
      struct.end
   struct.end
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_AddBurstFireModeEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_AddBurstFireModeEffect
   Text = Change fire type
   Type = EEffectType::ChangeFireTypes
   bIsPermanent = true
   FireTypes : struct.begin
      [0] = EFireType::Queue
      [1] = EFireType::Automatic
   struct.end
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = true
struct.end

BPRUE_SemiAutoOnlyEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SemiAutoOnlyEffect
   Text = Change fire type
   Type = EEffectType::ChangeFireTypes
   bIsPermanent = true
   FireTypes : struct.begin
      [0] = EFireType::SemiAutomatic
   struct.end
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = true
struct.end
'''
