from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "assault_rifles_upgrades.json"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_EffectPrototypes.cfg"
NPC_OUTPUT_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"
MODULE_TEMPLATE_SID = "BPRUE_ModuleTemplate"

POWER_CALIBER = {
    "A545": ("A762Sniper", "762", "sid_bprue_caliber_762_eastern_name", "sid_bprue_caliber_762_eastern_description", 2800),
    "A556": ("A762NATO", "762NATO", "sid_bprue_caliber_762_nato_name", "sid_bprue_caliber_762_nato_description", 3200),
}
CALIBER_EFFECTS = {
    "A762Sniper": ("ChangeCaliber762Effect", ("ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762NATOEffect", "ChangeAmmoTypesNo939Effect"), "ChangeAmmoTypes762Effect"),
    "A762NATO": ("BPRUE_ChangeCaliber762NATOEffect", ("ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"), "BPRUE_ChangeAmmoTypes762NATOEffect"),
}
DEFAULT_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"
CALIBER_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_CaliberChange.T_PDA_Upgrades_Icon_CaliberChange'"
MODULE_SPECS = (
    ("FireControl", "Burst", "Body", 3000, "sid_bprue_fire_control_burst_name", "sid_bprue_fire_control_burst_description", ("BPRUE_AddBurstFireModeEffect", "RecoilPos5Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    ("FireControl", "Precision", "Body", 3600, "sid_bprue_fire_control_precision_name", "sid_bprue_fire_control_precision_description", ("BPRUE_SemiAutoOnlyEffect", "BPRUE_DamagePos10Effect", "ArmorPiercingPos15Effect", "BPRUE_DurabilityPerShotNeg20Effect")),
    ("FireRate", "HighSpeed", "Barrel", 3400, "sid_bprue_fire_rate_high_speed_name", "sid_bprue_fire_rate_high_speed_description", ("BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect")),
    ("FireRate", "Balanced", "Barrel", 3200, "sid_bprue_fire_rate_balanced_name", "sid_bprue_fire_rate_balanced_description", ("BPRUE_FireIntervalNeg10Effect", "RecoilPos10Effect", "ShotRecoveryPos20Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    ("Reload", "Competition", "Body", 2800, "sid_bprue_reload_competition_name", "sid_bprue_reload_competition_description", ("BPRUE_ReloadingTimeNeg20Effect", "RecoilNeg15Effect")),
    ("Reload", "Reinforced", "Body", 3000, "sid_bprue_reload_reinforced_name", "sid_bprue_reload_reinforced_description", ("BPRUE_ReloadingTimeNeg10Effect", "DurabilityPerShotPos20Effect", "BPRUE_FireIntervalPos5Effect")),
    ("Stock", "Lightweight", "Stock", 3000, "sid_bprue_stock_lightweight_name", "sid_bprue_stock_lightweight_description", ("AimingTimePos15Effect", "AimingMovementPos10Effect", "RecoilNeg15Effect")),
    ("Stock", "Stabilized", "Stock", 3200, "sid_bprue_stock_stabilized_name", "sid_bprue_stock_stabilized_description", ("RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect")),
    ("Stock", "Marksman", "Stock", 3400, "sid_bprue_stock_marksman_name", "sid_bprue_stock_marksman_description", ("IdleSwayXPos20Effect", "IdleSwayYPos20Effect", "MaxDispersionPos15Effect", "AimingTimeNeg15Effect")),
)


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _definition(family: dict, group: str, variant: str, target: str, cost: int, text: str, hint: str, effects: tuple[str, ...], icon: str = DEFAULT_ICON) -> UpgradeDefinition:
    prefix = family["prototype_prefix"]
    return UpgradeDefinition(
        sid=f"{prefix}_Upgrade_BPRUE_{group}_{variant}", general_setup_sid=family["weapon_sid"],
        weapon_class="AR", group=group, target_part=target, text_sid=text, hint_sid=hint,
        image=family["image"], icon=icon, cost=cost, effects=effects, template_sid=MODULE_TEMPLATE_SID,
    )


def build_upgrades(config: dict) -> list[UpgradeDefinition]:
    result: list[UpgradeDefinition] = []
    for family in config["families"].values():
        family_upgrades: list[UpgradeDefinition] = []
        power = POWER_CALIBER.get(family["base_caliber"])
        if power:
            caliber, suffix, text, hint, cost = power
            change, removes, add = CALIBER_EFFECTS[caliber]
            family_upgrades.append(_definition(
                family, "Caliber", suffix, "Body", cost, text, hint,
                (change, *removes, add, "BPRUE_DamagePos10Effect", "RecoilNeg20Effect", "BPRUE_DurabilityPerShotNeg20Effect"), CALIBER_ICON,
            ))
        for spec in MODULE_SPECS:
            family_upgrades.append(_definition(family, *spec))

        by_group: dict[str, list[UpgradeDefinition]] = {}
        for upgrade in family_upgrades:
            by_group.setdefault(upgrade.group, []).append(upgrade)
        for upgrade in family_upgrades:
            siblings = tuple(item.sid for item in by_group[upgrade.group] if item.sid != upgrade.sid)
            result.append(UpgradeDefinition(**{**upgrade.__dict__, "blocking_sids": siblings}))
    return result


def configure_general_setups(config: dict, model: UpgradeBuildModel) -> None:
    for family in config["families"].values():
        model.configure_general_setup(family["weapon_sid"], FireQueueCount=3)


def render_effect_patch(config: dict) -> str:
    # Effect definitions are intentionally class-owned; the family config no longer duplicates them.
    return _EFFECTS


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
   ValueMin = 10%
   ValueMax = 10%
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_DurabilityPerShotNeg10Effect
   ValueMin = 10%
   ValueMax = 10%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_DurabilityPerShotNeg20Effect
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

BPRUE_ChangeCaliber762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_ChangeCaliber762NATOEffect
   Type = EEffectType::ChangeCaliber
   Caliber = EBulletCaliber::A762NATO
struct.end

BPRUE_ChangeAmmoTypes762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_ChangeAmmoTypes762NATOEffect
   AmmoTypeProjectiles : struct.begin
      [0] : struct.begin
         AmmoType = EAmmoType::Default
         ProjectilePrototypeSID = P762NATO
      struct.end
   struct.end
struct.end

BPRUE_ChangeAmmoTypesNo762Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_ChangeAmmoTypesNo762Effect
struct.end

BPRUE_ChangeAmmoTypesNo762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}
   SID = BPRUE_ChangeAmmoTypesNo762NATOEffect
struct.end

BPRUE_AddBurstFireModeEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_AddBurstFireModeEffect
   Type = EEffectType::AddFireMode
   FireMode = EFireMode::Burst
struct.end

BPRUE_SemiAutoOnlyEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SemiAutoOnlyEffect
   Type = EEffectType::RemoveFireMode
   FireMode = EFireMode::Auto
struct.end
'''


def render_npc_patch(config: dict, model: UpgradeBuildModel) -> str:
    technician = config["technician"]
    technician_sids = list(dict.fromkeys([technician["prototype_sid"], technician["all_prototype_sid"], *technician.get("concrete_prototype_sids", [])]))
    upgrades = model.technician_upgrades()
    lines = ["// AUTO-GENERATED - all BPRUE weapon specialization modules are available at all technicians.", ""]
    for technician_sid in technician_sids:
        lines += [f"{technician_sid} : struct.begin {{bpatch}}", "   Upgrades : struct.begin {bpatch}"]
        for upgrade in upgrades:
            lines += ["      [*] : struct.begin", f"         UpgradePrototypeSID = {upgrade.sid}", "         Enabled = true", "      struct.end"]
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)
