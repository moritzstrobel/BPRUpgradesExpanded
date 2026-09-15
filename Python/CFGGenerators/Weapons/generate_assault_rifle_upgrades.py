from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from upgrade_renderers import render_general_setup_patch, render_upgrade_prototypes

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "assault_rifles_upgrades.json"
UPGRADE_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_EffectPrototypes.cfg"
WEAPON_OUTPUT_PATH = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
NPC_OUTPUT_PATH = CONTENT_ROOT / "GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg"

MODULE_TEMPLATE_SID = "BPRUE_ModuleTemplate"
EASTERN_POWER_FAMILIES = {"AK74", "Fora", "Dnipro"}
WESTERN_POWER_FAMILIES = {"G37", "M16", "Kharod", "Arev"}
NINE_BY_THIRTY_NINE_FAMILIES = {"Gvintar", "Grim", "Lavina"}

CALIBER_EFFECTS = {
    "A762Sniper": {
        "change": "ChangeCaliber762Effect",
        "add_ammo": "ChangeAmmoTypes762Effect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762NATOEffect", "ChangeAmmoTypesNo939Effect"],
    },
    "A762NATO": {
        "change": "BPRUE_ChangeCaliber762NATOEffect",
        "add_ammo": "BPRUE_ChangeAmmoTypes762NATOEffect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"],
    },
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def module_template(family: dict) -> dict:
    modules = family.get("modules", [])
    if modules:
        return dict(modules[0])
    standard = family.get("standard_upgrades", [])
    if standard:
        return dict(standard[0])
    raise ValueError(f"No source upgrade available for {family['prototype_prefix']}")


def make_power_caliber_module(family_name: str, family: dict) -> dict | None:
    if family_name in NINE_BY_THIRTY_NINE_FAMILIES or family_name not in EASTERN_POWER_FAMILIES | WESTERN_POWER_FAMILIES:
        return None
    module = module_template(family)
    module.update({"kind": "caliber", "horizontal_position": 0, "vertical_position": "EUpgradeVerticalPosition::Top", "target_part": "EUpgradeTargetPartType::Body", "balance_class": "power"})
    prefix = family["prototype_prefix"]
    if family_name in EASTERN_POWER_FAMILIES:
        module.update({"sid": f"{prefix}_Upgrade_BPRUE_Caliber_762", "text_sid": "sid_bprue_caliber_762_eastern_name", "hint_sid": "sid_bprue_caliber_762_eastern_description", "caliber": "A762Sniper", "base_cost": 2800})
    else:
        module.update({"sid": f"{prefix}_Upgrade_BPRUE_Caliber_762NATO", "text_sid": "sid_bprue_caliber_762_nato_name", "hint_sid": "sid_bprue_caliber_762_nato_description", "caliber": "A762NATO", "base_cost": 3200})
    return module


def make_reload_modules(family: dict) -> list[dict]:
    template = module_template(family); prefix = family["prototype_prefix"]
    competition = dict(template); competition.update({"kind": "reload_competition", "sid": f"{prefix}_Upgrade_BPRUE_Reload_Competition", "text_sid": "sid_bprue_reload_competition_name", "hint_sid": "sid_bprue_reload_competition_description", "base_cost": 2800, "vertical_position": "EUpgradeVerticalPosition::Down", "target_part": "EUpgradeTargetPartType::Body"})
    reinforced = dict(template); reinforced.update({"kind": "reload_reinforced", "sid": f"{prefix}_Upgrade_BPRUE_Reload_Reinforced", "text_sid": "sid_bprue_reload_reinforced_name", "hint_sid": "sid_bprue_reload_reinforced_description", "base_cost": 3000, "vertical_position": "EUpgradeVerticalPosition::Down", "target_part": "EUpgradeTargetPartType::Body"})
    return [competition, reinforced]


def make_fire_rate_modules(family: dict) -> list[dict]:
    template = module_template(family); prefix = family["prototype_prefix"]
    high_speed = dict(template); high_speed.update({"kind": "fire_rate_high_speed", "sid": f"{prefix}_Upgrade_BPRUE_FireRate_HighSpeed", "text_sid": "sid_bprue_fire_rate_high_speed_name", "hint_sid": "sid_bprue_fire_rate_high_speed_description", "base_cost": 3400, "vertical_position": "EUpgradeVerticalPosition::Top", "target_part": "EUpgradeTargetPartType::Barrel"})
    balanced = dict(template); balanced.update({"kind": "fire_rate_balanced", "sid": f"{prefix}_Upgrade_BPRUE_FireRate_Balanced", "text_sid": "sid_bprue_fire_rate_balanced_name", "hint_sid": "sid_bprue_fire_rate_balanced_description", "base_cost": 3200, "vertical_position": "EUpgradeVerticalPosition::Top", "target_part": "EUpgradeTargetPartType::Barrel"})
    return [high_speed, balanced]


def make_fire_control_modules(family: dict) -> list[dict]:
    template = module_template(family); prefix = family["prototype_prefix"]
    burst = dict(template); burst.update({"kind": "fire_control_burst", "sid": f"{prefix}_Upgrade_BPRUE_FireControl_Burst", "text_sid": "sid_bprue_fire_control_burst_name", "hint_sid": "sid_bprue_fire_control_burst_description", "base_cost": 3000, "vertical_position": "EUpgradeVerticalPosition::Top", "target_part": "EUpgradeTargetPartType::Body"})
    precision = dict(template); precision.update({"kind": "fire_control_precision", "sid": f"{prefix}_Upgrade_BPRUE_FireControl_Precision", "text_sid": "sid_bprue_fire_control_precision_name", "hint_sid": "sid_bprue_fire_control_precision_description", "base_cost": 3600, "vertical_position": "EUpgradeVerticalPosition::Top", "target_part": "EUpgradeTargetPartType::Body"})
    return [burst, precision]


def make_stock_modules(family: dict) -> list[dict]:
    template = module_template(family); prefix = family["prototype_prefix"]
    result = []
    for key, cost in (("Lightweight", 3000), ("Stabilized", 3200), ("Marksman", 3400)):
        module = dict(template)
        module.update({"kind": f"stock_{key.lower()}", "sid": f"{prefix}_Upgrade_BPRUE_Stock_{key}", "text_sid": f"sid_bprue_stock_{key.lower()}_name", "hint_sid": f"sid_bprue_stock_{key.lower()}_description", "base_cost": cost, "vertical_position": "EUpgradeVerticalPosition::Down", "target_part": "EUpgradeTargetPartType::Stock"})
        result.append(module)
    return result


def family_modules(family_name: str, family: dict) -> list[dict]:
    result: list[dict] = []
    caliber = make_power_caliber_module(family_name, family)
    if caliber:
        result.append(caliber)
    result.extend(make_fire_control_modules(family))
    result.extend(make_fire_rate_modules(family))
    result.extend(make_reload_modules(family))
    result.extend(make_stock_modules(family))
    return result


def caliber_module_effects(module: dict) -> list[str]:
    effects = CALIBER_EFFECTS[module["caliber"]]
    result = [effects["change"], *effects["remove_ammo"], effects["add_ammo"]]
    if module.get("balance_class") == "power":
        result += ["BPRUE_DamagePos10Effect", "RecoilNeg20Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    return result


def module_effects(module: dict) -> list[str]:
    kind = module.get("kind")
    if kind == "caliber": return caliber_module_effects(module)
    if kind == "reload_competition": return ["BPRUE_ReloadingTimeNeg20Effect", "RecoilNeg15Effect"]
    if kind == "reload_reinforced": return ["BPRUE_ReloadingTimeNeg10Effect", "DurabilityPerShotPos20Effect", "BPRUE_FireIntervalPos5Effect"]
    if kind == "fire_rate_high_speed": return ["BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    if kind == "fire_rate_balanced": return ["BPRUE_FireIntervalNeg10Effect", "RecoilPos10Effect", "ShotRecoveryPos20Effect", "BPRUE_DurabilityPerShotNeg10Effect"]
    if kind == "fire_control_burst": return ["BPRUE_AddBurstFireModeEffect", "RecoilPos5Effect", "BPRUE_DurabilityPerShotNeg10Effect"]
    if kind == "fire_control_precision": return ["BPRUE_SemiAutoOnlyEffect", "BPRUE_DamagePos10Effect", "ArmorPiercingPos15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    if kind == "stock_lightweight": return ["AimingTimePos15Effect", "AimingMovementPos10Effect", "RecoilNeg15Effect"]
    if kind == "stock_stabilized": return ["RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]
    if kind == "stock_marksman": return ["IdleSwayXPos20Effect", "IdleSwayYPos20Effect", "MaxDispersionPos15Effect", "AimingTimeNeg15Effect"]
    raise ValueError(f"Unknown AR module kind: {kind}")


def module_group(kind: str) -> str:
    if kind.startswith("reload_"): return "Reload"
    if kind.startswith("fire_rate_"): return "FireRate"
    if kind.startswith("fire_control_"): return "FireControl"
    if kind.startswith("stock_"): return "Stock"
    return "Caliber"


def enum_value(value: str) -> str:
    return value.rsplit("::", 1)[-1]


def build_upgrades(config: dict) -> list[UpgradeDefinition]:
    result: list[UpgradeDefinition] = []
    for family_name, family in config["families"].items():
        modules = family_modules(family_name, family)
        by_group: dict[str, list[dict]] = {}
        for module in modules:
            by_group.setdefault(module_group(module["kind"]), []).append(module)

        for module in modules:
            group = module_group(module["kind"])
            result.append(UpgradeDefinition(
                sid=module["sid"],
                general_setup_sid=family["weapon_sid"],
                weapon_class="AR",
                group=group,
                target_part=enum_value(module["target_part"]),
                text_sid=module["text_sid"],
                hint_sid=module["hint_sid"],
                image=module["image"],
                icon=module["icon"],
                cost=module["base_cost"],
                effects=tuple(module_effects(module)),
                blocking_sids=tuple(other["sid"] for other in by_group[group] if other["sid"] != module["sid"]),
                vertical_position=enum_value(module["vertical_position"]),
                template_sid=MODULE_TEMPLATE_SID,
            ))
    return result


def configure_general_setups(config: dict, model: UpgradeBuildModel) -> None:
    for family_name, family in config["families"].items():
        modules = family_modules(family_name, family)
        if any(module_group(module["kind"]) == "FireControl" for module in modules):
            model.configure_general_setup(
                family["weapon_sid"],
                FireQueueCount=family.get("fire_queue_count", 3),
            )


def render_effect_patch(config: dict) -> str:
    return """// -----------------------------------------------------------------------------
// AUTO-GENERATED FILE - DO NOT EDIT BY HAND
// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json
// Generated by: generate_assault_rifle_upgrades.py
// -----------------------------------------------------------------------------

BPRUE_FireIntervalNeg10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_FireIntervalNeg10Effect
   Text = Increase Fire Rate
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
   Text = Increase Fire Rate
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
   Text = Decrease Fire Rate
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
   Text = Decrease Reloading Time
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
   Text = Decrease Reloading Time
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = -10%
   ValueMax = -10%
   bIsPermanent = true
   Positive = EBeneficial::Positive
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_AddBurstFireModeEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeFireTypeTemplate}
   SID = BPRUE_AddBurstFireModeEffect
   LocalizationSID = bprue_fire_modes
   FireTypes : struct.begin
      [0] = EFireType::SemiAutomatic
      [1] = EFireType::Queue
      [2] = EFireType::Automatic
   struct.end
   ShowUpgradeEffectValue = false
struct.end

BPRUE_SemiAutoOnlyEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeFireTypeTemplate}
   SID = BPRUE_SemiAutoOnlyEffect
   LocalizationSID = bprue_semi_auto_only
   FireTypes : struct.begin
      [0] = EFireType::SemiAutomatic
   struct.end
   ShowUpgradeEffectValue = false
struct.end

BPRUE_ChangeCaliber762NATOEffect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeCaliberTemplate}
   SID = BPRUE_ChangeCaliber762NATOEffect
   Caliber = EAmmoCaliber::A762NATO
   ShowUpgradeEffectValue = false
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
   Positive = EBeneficial::Positive
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
"""


def render_appended_upgrade_entries(upgrades: list[UpgradeDefinition], indent: str = "      ") -> list[str]:
    lines: list[str] = []
    for upgrade in upgrades:
        lines += [f"{indent}[*] : struct.begin", f"{indent}   UpgradePrototypeSID = {upgrade.sid}", f"{indent}   Enabled = true", f"{indent}struct.end"]
    return lines


def render_npc_patch(config: dict, model: UpgradeBuildModel) -> str:
    technician = config["technician"]
    upgrades = model.technician_upgrades()
    lines = ["// AUTO-GENERATED - Source: UpgradeBuildModel", "", "// Draft setup: all BPRUE assault-rifle modules are available at all technicians.", ""]
    prototype_sids = [technician["prototype_sid"], technician["all_prototype_sid"], *technician.get("concrete_prototype_sids", [])]
    seen: set[str] = set()
    for prototype_sid in prototype_sids:
        if prototype_sid in seen:
            continue
        seen.add(prototype_sid)
        lines += [f"{prototype_sid} : struct.begin {{bpatch}}", "   Upgrades : struct.begin {bpatch}"]
        lines += render_appended_upgrade_entries(upgrades)
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def main() -> None:
    config = load_config()
    model = UpgradeBuildModel()
    model.extend(build_upgrades(config))
    configure_general_setups(config, model)
    model.validate()

    outputs = {
        UPGRADE_OUTPUT_PATH: render_upgrade_prototypes(
            model,
            source="assault_rifles_upgrades.json",
            template_sid=MODULE_TEMPLATE_SID,
            header_comments=(
                "Assault-rifle BPRUE extensions are technician modules.",
                "Module categories are permanent specialization choices: sibling options block each other.",
            ),
        ),
        EFFECT_OUTPUT_PATH: render_effect_patch(config),
        WEAPON_OUTPUT_PATH: render_general_setup_patch(model),
        NPC_OUTPUT_PATH: render_npc_patch(config, model),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")
    print(f"Generated assault-rifle CFGs from {model.summary()}")


if __name__ == "__main__":
    main()
