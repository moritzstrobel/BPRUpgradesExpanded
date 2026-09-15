from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeDefinition

CATALOG_PATH = Path(__file__).with_name("specialization_module_catalog.json")

# Concrete effect bundles used by the generators. Vanilla effects are reused where
# possible; BPRUE_Shared_* counterparts are emitted by render_shared_effects().
MODULE_EFFECTS = {
    "lightweight_assembly": ("WeightDown15Effect", "AimingTimePos10Effect", "BPRUE_Shared_RecoilPenalty8Effect"),
    "reinforced_assembly": ("RecoilPos10Effect", "DurabilityPos10Effect", "BPRUE_Shared_WeightPenalty10Effect"),
    "recoil_control": ("RecoilPos15Effect", "BPRUE_Shared_DispersionPenalty5Effect"),
    "precision_tuning": ("DispersionPos15Effect", "BPRUE_Shared_RecoilPenalty8Effect"),
    "high_cyclic_system": ("BPRUE_Shared_FireIntervalNeg12Effect", "BPRUE_Shared_RecoilPenalty10Effect", "BPRUE_Shared_DurabilityPerShotPenalty8Effect"),
    "controlled_action": ("BPRUE_Shared_FireIntervalPenalty10Effect", "RecoilPos10Effect", "DispersionPos10Effect"),
    "soft_target": ("DamagePos15Effect", "FlatnessUp10Effect", "ProjectileSpeedPos10Effect", "BPRUE_Shared_ArmorPiercingPenalty20Effect"),
    "armor_piercing": ("ArmorPiercingPos25Effect", "CoverPiercingPos20Effect", "BPRUE_Shared_DamagePenalty10Effect"),
    "hardened_components": ("DurabilityPos20Effect", "BPRUE_Shared_WeightPenalty5Effect"),
    "lightweight_components": ("BPRUE_Shared_WeightDown12Effect", "BPRUE_Shared_DurabilityPenalty15Effect", "BPRUE_Shared_AimingTimePos8Effect"),
    "cqb_configuration": ("AimingTimePos15Effect", "DispersionPos10Effect", "BPRUE_Shared_FlatnessPenalty10Effect"),
    "range_configuration": ("FlatnessUp15Effect", "DispersionPos10Effect", "BPRUE_Shared_AimingTimePenalty10Effect"),
}

GROUP_META = {
    "handling": ("Handling", "Body", "Down", 3000),
    "recoil_precision": ("Precision", "Barrel", "Top", 3200),
    "action": ("ActionProfile", "Barrel", "Top", 3400),
    "ballistics": ("BallisticsProfile", "Barrel", "Top", 3600),
    "reliability": ("Reliability", "Body", "Down", 3000),
    "range_profile": ("RangeProfile", "Barrel", "Top", 3400),
}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _token(value: str) -> str:
    return value.title().replace("_", "")


def build_shared_specializations(*, families: dict, class_key: str, weapon_class: str,
                                 template_sid: str, image_for_family, icon: str,
                                 sid_namespace: str, cost_scale_key: str = "cost_scale") -> list[UpgradeDefinition]:
    catalog = load_catalog()
    result: list[UpgradeDefinition] = []
    for family in families.values():
        prefix = family["prototype_prefix"]
        setup = family["general_setup_sid"]
        scale = family.get(cost_scale_key, 1.0)
        for group_key in catalog["weapon_class_groups"][class_key]:
            group_name, target, vertical, base_cost = GROUP_META[group_key]
            modules = catalog["groups"][group_key]["modules"]
            group_sids = [f"{prefix}_Upgrade_BPRUE_{sid_namespace}_{group_name}_{_token(key)}" for key in modules]
            for key in modules:
                current = f"{prefix}_Upgrade_BPRUE_{sid_namespace}_{group_name}_{_token(key)}"
                result.append(UpgradeDefinition(
                    sid=current,
                    general_setup_sid=setup,
                    weapon_class=weapon_class,
                    group=group_name,
                    target_part=target,
                    text_sid=f"sid_bprue_shared_{key}_name",
                    hint_sid=f"sid_bprue_shared_{key}_description",
                    image=image_for_family(family),
                    icon=icon,
                    cost=round(base_cost * scale),
                    effects=MODULE_EFFECTS[key],
                    blocking_sids=tuple(s for s in group_sids if s != current),
                    vertical_position=vertical,
                    template_sid=template_sid,
                ))
    return result


def render_shared_effects() -> str:
    defs = [
        ("BPRUE_Shared_RecoilPenalty8Effect", "Recoil", "8%", "Negative", "bprue_recoil"),
        ("BPRUE_Shared_RecoilPenalty10Effect", "Recoil", "10%", "Negative", "bprue_recoil"),
        ("BPRUE_Shared_WeightPenalty5Effect", "WeaponItemWeight", "5%", "Negative", "bprue_weight"),
        ("BPRUE_Shared_WeightPenalty10Effect", "WeaponItemWeight", "10%", "Negative", "bprue_weight"),
        ("BPRUE_Shared_WeightDown12Effect", "WeaponItemWeight", "-12%", "Positive", "bprue_weight"),
        ("BPRUE_Shared_DispersionPenalty5Effect", "Dispersion", "5%", "Negative", "bprue_accuracy"),
        ("BPRUE_Shared_FireIntervalNeg12Effect", "FireInterval", "-12%", "Positive", "bprue_fire_rate"),
        ("BPRUE_Shared_FireIntervalPenalty10Effect", "FireInterval", "10%", "Negative", "bprue_fire_rate"),
        ("BPRUE_Shared_DurabilityPerShotPenalty8Effect", "DurabilityPerShot", "8%", "Negative", "bprue_weapon_wear"),
        ("BPRUE_Shared_ArmorPiercingPenalty20Effect", "ArmorPiercing", "-20%", "Negative", "bprue_armor_piercing"),
        ("BPRUE_Shared_DamagePenalty10Effect", "WeaponDamage", "-10%", "Negative", "bprue_damage"),
        ("BPRUE_Shared_DurabilityPenalty15Effect", "Durability", "-15%", "Negative", "bprue_durability"),
        ("BPRUE_Shared_AimingTimePos8Effect", "AimingTime", "-8%", "Positive", "bprue_aiming_speed"),
        ("BPRUE_Shared_AimingTimePenalty10Effect", "AimingTime", "10%", "Negative", "bprue_aiming_speed"),
        ("BPRUE_Shared_FlatnessPenalty10Effect", "EffectiveFireDistance", "-10%", "Negative", "bprue_effective_range"),
    ]
    lines = ["// AUTO-GENERATED - shared specialization effects", ""]
    for sid, effect_type, value, beneficial, loc in defs:
        lines += [
            f"{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}",
            f"   SID = {sid}", f"   Type = EEffectType::{effect_type}", f"   LocalizationSID = {loc}",
            f"   ValueMin = {value}", f"   ValueMax = {value}", "   bIsPermanent = true",
            f"   Positive = EBeneficial::{beneficial}", "   ShowUpgradeEffectValue = true",
            "   ShowUpgradeEffect = true", "struct.end", "",
        ]
    return "\n".join(lines)
