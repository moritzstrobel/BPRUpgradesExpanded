from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition

CONFIG_PATH = Path(__file__).with_name("unique_weapons.json")
SIGNATURE_CONFIG_PATH = Path(__file__).with_name("unique_signatures.json")

CLASS_CONFIG_KEYS = {
    "AssaultRifles": "ar",
    "SMGs": "smg",
    "Shotguns": "shotgun",
    "Pistols": "pistol",
    "Snipers": "sniper",
    "MachineGuns": "machine_gun",
}
WEAPON_CLASS_CODES = {
    "AssaultRifles": "AR",
    "SMGs": "SMG",
    "Shotguns": "Shotgun",
    "Pistols": "Pistol",
    "Snipers": "Sniper",
    "MachineGuns": "MachineGun",
}


def load_unique_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_signature_config() -> dict:
    return json.loads(SIGNATURE_CONFIG_PATH.read_text(encoding="utf-8"))


def _unique_prefix(name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", name)
    return f"BPRUEUnique{token}"


def _clone_sid(source_sid: str, base_prefix: str, unique_prefix: str) -> str:
    if not source_sid.startswith(base_prefix):
        raise ValueError(f"Cannot clone {source_sid}: expected base prefix {base_prefix}")
    return unique_prefix + source_sid[len(base_prefix):]


def add_unique_modules(model: UpgradeBuildModel, configs: dict) -> int:
    """Clone BPRUE base-family modules for supported Uniques.

    Physical pistol-slot conversions are baseline-only: their converted ItemPrototype
    variants exist only for explicitly supported base weapons, never for Uniques.
    """
    unique_config = load_unique_config()
    source_by_setup = model.by_general_setup()
    added = 0

    for unique_name, unique in unique_config.get("uniques", {}).items():
        class_name = unique["class"]
        config_key = CLASS_CONFIG_KEYS.get(class_name)
        if not config_key or config_key not in configs:
            raise ValueError(f"{unique_name}: no loaded generator config for class {class_name}")
        class_config = configs[config_key]
        base_name = unique["base_family"]
        base = class_config.get("families", {}).get(base_name)
        if not base:
            raise ValueError(f"{unique_name}: unknown {class_name} base_family {base_name}")

        base_setup = base["general_setup_sid"]
        base_prefix = base["prototype_prefix"]
        source_upgrades = [
            upgrade for upgrade in source_by_setup.get(base_setup, [])
            if upgrade.group != "Conversion"
        ]
        if not source_upgrades:
            raise ValueError(f"{unique_name}: base family {base_name} ({base_setup}) has no BPRUE upgrades")

        unique_setup = unique["general_setup_sid"]
        unique_prefix = unique.get("prototype_prefix", _unique_prefix(unique_name))
        sid_map = {u.sid: _clone_sid(u.sid, base_prefix, unique_prefix) for u in source_upgrades}

        for source in source_upgrades:
            cloned = replace(
                source,
                sid=sid_map[source.sid],
                general_setup_sid=unique_setup,
                additional_general_setup_sids=(),
                blocking_sids=tuple(sid_map.get(sid, sid) for sid in source.blocking_sids),
                horizontal_position=None,
            )
            model.add(cloned)
            added += 1

    return added


def add_unique_signatures(model: UpgradeBuildModel) -> int:
    """Add the one-off BPRUE signature module defined for each supported Unique."""
    uniques = load_unique_config().get("uniques", {})
    signatures = load_signature_config().get("signatures", {})
    added = 0

    unknown = sorted(set(signatures) - set(uniques))
    if unknown:
        raise ValueError("Unique signatures reference unknown weapons: " + ", ".join(unknown))

    for unique_name, signature in signatures.items():
        unique = uniques[unique_name]
        class_name = unique["class"]
        weapon_class = WEAPON_CLASS_CODES.get(class_name)
        if not weapon_class:
            raise ValueError(f"{unique_name}: unsupported Unique signature class {class_name}")
        token = re.sub(r"[^A-Za-z0-9]", "", unique_name)
        key_token = "".join(part.capitalize() for part in signature["key"].split("_"))
        model.add(UpgradeDefinition(
            sid=f"BPRUEUnique{token}_Upgrade_BPRUE_Signature_{key_token}",
            general_setup_sid=unique["general_setup_sid"],
            weapon_class=weapon_class,
            group="Signature",
            target_part=signature["target_part"],
            text_sid=f"sid_bprue_unique_{signature['key']}_name",
            hint_sid=f"sid_bprue_unique_{signature['key']}_description",
            image="",
            icon="Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Depreciation.T_PDA_Upgrades_Icon_Depreciation'",
            cost=int(signature["cost"]),
            effects=tuple(signature["effects"]),
            template_sid="BPRUE_ModuleTemplate",
            standalone=True,
        ))
        added += 1
    return added


def render_unique_signature_effects() -> str:
    """Render only effects that do not already exist in Vanilla/class/shared pools."""
    return r'''// AUTO-GENERATED - BPRUE Unique signature effects

BPRUE_Unique_WeightDown20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_WeightDown20Effect
   Type = EEffectType::WeaponItemWeight
   LocalizationSID = bprue_weight
   ValueMin = -20%
   ValueMax = -20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
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

BPRUE_Unique_AimingTimePos30Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_AimingTimePos30Effect
   Type = EEffectType::AimingTime
   LocalizationSID = bprue_aiming_speed
   ValueMin = -30%
   ValueMax = -30%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_FireIntervalNeg15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_FireIntervalNeg15Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = -15%
   ValueMax = -15%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_FireIntervalNeg25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_FireIntervalNeg25Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = -25%
   ValueMax = -25%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_ReloadingTimeNeg15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_ReloadingTimeNeg15Effect
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = -15%
   ValueMax = -15%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_DamagePos20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_DamagePos20Effect
   Type = EEffectType::WeaponDamage
   LocalizationSID = bprue_damage
   ValueMin = 20%
   ValueMax = 20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_RecoilPos30Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_RecoilPos30Effect
   Type = EEffectType::Recoil
   LocalizationSID = bprue_recoil
   ValueMin = -30%
   ValueMax = -30%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_EffectiveRangePos15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_EffectiveRangePos15Effect
   Type = EEffectType::EffectiveFireDistance
   LocalizationSID = bprue_effective_range
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_RecoilPenalty15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_RecoilPenalty15Effect
   Type = EEffectType::Recoil
   LocalizationSID = bprue_recoil
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_ArmorPiercingPos20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_ArmorPiercingPos20Effect
   Type = EEffectType::ArmorPiercing
   LocalizationSID = bprue_armor_piercing
   ValueMin = 20%
   ValueMax = 20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_WeightPenalty20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_WeightPenalty20Effect
   Type = EEffectType::WeaponItemWeight
   LocalizationSID = bprue_weight
   ValueMin = 20%
   ValueMax = 20%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_DurabilityPerShotNeg25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_Unique_DurabilityPerShotNeg25Effect
   LocalizationSID = bprue_weapon_wear
   ValueMin = 25%
   ValueMax = 25%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_DurabilityPos30Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_DurabilityPos30Effect
   Type = EEffectType::Durability
   LocalizationSID = bprue_durability
   ValueMin = 30%
   ValueMax = 30%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_EffectiveRangePos20Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_EffectiveRangePos20Effect
   Type = EEffectType::EffectiveFireDistance
   LocalizationSID = bprue_effective_range
   ValueMin = 20%
   ValueMax = 20%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_AimingMovementPos25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_AimingMovementPos25Effect
   Type = EEffectType::AimingMovementSpeed
   LocalizationSID = bprue_aiming_movement
   ValueMin = 25%
   ValueMax = 25%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_AimingTimePos25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_AimingTimePos25Effect
   Type = EEffectType::AimingTime
   LocalizationSID = bprue_aiming_speed
   ValueMin = -25%
   ValueMax = -25%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_DispersionPos30Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_DispersionPos30Effect
   Type = EEffectType::Dispersion
   LocalizationSID = bprue_dispersion
   ValueMin = -30%
   ValueMax = -30%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_DurabilityPerShotPos25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}
   SID = BPRUE_Unique_DurabilityPerShotPos25Effect
   LocalizationSID = bprue_weapon_wear
   ValueMin = -25%
   ValueMax = -25%
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_WeightPenalty15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_WeightPenalty15Effect
   Type = EEffectType::WeaponItemWeight
   LocalizationSID = bprue_weight
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_Unique_SemiBurstOnlyEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Unique_SemiBurstOnlyEffect
   Text = Change fire type
   Type = EEffectType::ChangeFireTypes
   LocalizationSID = bprue_fire_modes_semi_burst
   bIsPermanent = true
   FireTypes : struct.begin
      [0] = EFireType::SemiAutomatic
      [1] = EFireType::Queue
   struct.end
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = true
struct.end
'''
