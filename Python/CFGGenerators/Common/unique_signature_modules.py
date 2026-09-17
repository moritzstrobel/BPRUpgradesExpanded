from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition

MODULE_TEMPLATE_SID = "BPRUE_ModuleTemplate"
DEFAULT_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"
UNIQUE_CONFIG_PATH = Path(__file__).with_name("unique_weapons.json")

# One deliberately stronger, non-blocking endgame module per Unique. Signatures
# are added after the normal base-family modules have been cloned, so they never
# become part of the clone source set themselves.
AR_SIGNATURES = {
    "AK74Phantom": ("GhostMechanism", "Body", 5200, "ghost_mechanism", ("WeightDown15Effect", "AimingTimePos15Effect", "AimingMovementPos10Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    "AK74Strelok": ("StreloksRefinement", "Body", 5400, "streloks_refinement", ("WeightDown15Effect", "AimingTimePos15Effect", "BPRUE_ReloadingTimeNeg10Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    "ArevPrecise": ("PrecisionConversion", "Barrel", 6200, "precision_conversion", ("BPRUE_SemiAutoOnlyEffect", "DispersionPos25Effect", "RecoilPos20Effect", "ProjectileSpeedPos20Effect")),
    "G37V2": ("BurstOptimizer", "Body", 6000, "burst_optimizer", ("BPRUE_Unique_SemiBurstFireTypesEffect", "RecoilPos20Effect", "DispersionPos15Effect", "BPRUE_ReloadingTimeNeg10Effect")),
    "Combatant": ("CombatHandlingPackage", "Body", 5600, "combat_handling_package", ("AimingMovementPos15Effect", "BPRUE_Unique_AimingTimePos20Effect", "RecoilPos15Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    "Decider": ("OverpressureSystem", "Barrel", 6400, "overpressure_system", ("DamagePos15Effect", "ArmorPiercingPos15Effect", "ProjectileSpeedPos10Effect", "BPRUE_RecoilPenalty20Effect", "BPRUE_DurabilityPerShotNeg15Effect")),
    "Drowned": ("FieldRiggedFeed", "Body", 5200, "field_rigged_feed", ("BPRUE_ReloadingTimeNeg20Effect", "BPRUE_Shared_WeightPenalty10Effect")),
    "Lummox": ("JuryRiggedAction", "Body", 5000, "jury_rigged_action", ("BPRUE_FireIntervalNeg20Effect", "RecoilPos15Effect", "BPRUE_ReloadingTimeNeg10Effect", "BPRUE_Unique_DurabilityPerShotPenalty25Effect")),
    "Merc": ("ContractorPackage", "Body", 5800, "contractor_package", ("DispersionPos15Effect", "RecoilPos15Effect", "AimingTimePos15Effect", "BPRUE_DurabilityPerShotNeg10Effect")),
    "S15": ("HighVelocity545System", "Barrel", 6200, "high_velocity_545_system", ("ProjectileSpeedPos20Effect", "ArmorPiercingPos15Effect", "DispersionPos10Effect", "BPRUE_RecoilPenalty15Effect")),
    "SOFMOD": ("SpecialOperationsPackage", "Body", 6000, "special_operations_package", ("AimingTimePos15Effect", "AimingMovementPos15Effect", "RecoilPos10Effect", "BPRUE_Shared_WeightPenalty10Effect")),
    "Sharpshooter": ("MatchFireControlGroup", "Body", 6400, "match_fire_control_group", ("BPRUE_Unique_SemiBurstFireTypesEffect", "DispersionPos25Effect", "RecoilPos20Effect", "ProjectileSpeedPos10Effect")),
    "Sotnyk": ("MasterGunsmithTuning", "Body", 7000, "master_gunsmith_tuning", ("RecoilPos15Effect", "DispersionPos15Effect", "BPRUE_ReloadingTimeNeg10Effect", "AimingTimePos10Effect", "BPRUE_DurabilityPerShotNeg15Effect")),
    "Trophy": ("ZoneHardenedInternals", "Body", 5800, "zone_hardened_internals", ("DurabilityPos30Effect", "DurabilityPerShotPos20Effect", "BPRUE_Shared_WeightPenalty10Effect")),
    "Unknown": ("ExperimentalGasSystem", "Barrel", 6000, "experimental_gas_system", ("BPRUE_FireIntervalNeg15Effect", "RecoilPos20Effect", "ProjectileSpeedPos10Effect", "BPRUE_DurabilityPerShotNeg20Effect")),
}


def _prefix(name: str) -> str:
    return "BPRUEUnique" + "".join(ch for ch in name if ch.isalnum())


def add_unique_signatures(model: UpgradeBuildModel, configs: dict) -> int:
    registry = json.loads(UNIQUE_CONFIG_PATH.read_text(encoding="utf-8")).get("uniques", {})
    ar_families = configs["ar"].get("families", {})
    added = 0
    for name, (suffix, target, cost, loc, effects) in AR_SIGNATURES.items():
        unique = registry.get(name)
        if not unique:
            raise ValueError(f"Unique signature {name}: missing central registry entry")
        if unique.get("class") != "AssaultRifles":
            raise ValueError(f"Unique signature {name}: expected AssaultRifles, got {unique.get('class')}")
        family = ar_families.get(unique["base_family"])
        if not family:
            raise ValueError(f"Unique signature {name}: missing AR base family {unique['base_family']}")
        model.add(UpgradeDefinition(
            sid=f"{_prefix(name)}_Upgrade_BPRUE_UniqueSignature_{suffix}",
            general_setup_sid=unique["general_setup_sid"],
            weapon_class="AR",
            group="UniqueSignature",
            target_part=target,
            text_sid=f"sid_bprue_unique_{loc}_name",
            hint_sid=f"sid_bprue_unique_{loc}_description",
            image=family["image"],
            icon=DEFAULT_ICON,
            cost=cost,
            effects=tuple(effects),
            template_sid=MODULE_TEMPLATE_SID,
            standalone=True,
        ))
        added += 1
    return added


def render_unique_signature_effects() -> str:
    return r'''// BPRUE Unique signature effects

BPRUE_Unique_SemiBurstFireTypesEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_SemiBurstFireTypesEffect
   Type = EEffectType::ChangeFireTypes
   LocalizationSID = bprue_fire_modes_semi_burst
   FireTypes : struct.begin
      [0] = EFireType::SemiAutomatic
      [1] = EFireType::Queue
   struct.end
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_DurabilityPerShotPenalty25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_Unique_DurabilityPerShotPenalty25Effect
   LocalizationSID = bprue_weapon_wear
   ValueMin = 25%
   ValueMax = 25%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_AimingTimePos20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_AimingTimePos20Effect
   Type = EEffectType::AimingTime
   LocalizationSID = bprue_aiming_speed
   ValueMin = -20%
   ValueMax = -20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_FireIntervalNeg15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_FireIntervalNeg15Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = -15%
   ValueMax = -15%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_RecoilPenalty15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=RecoilTemplate}
   SID = BPRUE_RecoilPenalty15Effect
   LocalizationSID = bprue_recoil
   ValueMin = -15%
   ValueMax = -15%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
'''
