from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent

CONFIG_PATH = SCRIPT_DIR / "assault_rifles_upgrades.json"
UPGRADE_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "UpgradePrototypes" / "UpgradePrototypes_patch_BPRUE.cfg"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "EffectPrototypes" / "EffectPrototypes_patch_BPRUE.cfg"
WEAPON_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "WeaponData" / "WeaponGeneralSetupPrototypes" / "WeaponGeneralSetupPrototypes_patch_BPRUE.cfg"
NPC_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "NPCPrototypes" / "NPCPrototypes_patch_BPRUE.cfg"

UPGRADE_TEMPLATE_SID = "BPRUE_UpgradeTemplate"
MODULE_TEMPLATE_SID = "BPRUE_ModuleTemplate"

EASTERN_POWER_FAMILIES = {"AK74", "Fora", "Dnipro"}
WESTERN_POWER_FAMILIES = {"G37", "M16", "Kharod", "Arev"}
NINE_BY_THIRTY_NINE_FAMILIES = {"Gvintar", "Grim", "Lavina"}

CALIBER_EFFECTS = {
    "A762Sniper": {
        "change": "ChangeCaliber762Effect",
        "add_ammo": "ChangeAmmoTypes762Effect",
        "remove_ammo": [
            "ChangeAmmoTypesNo545Effect",
            "ChangeAmmoTypesNo556Effect",
            "BPRUE_ChangeAmmoTypesNo762NATOEffect",
            "ChangeAmmoTypesNo939Effect",
        ],
    },
    "A762NATO": {
        "change": "BPRUE_ChangeCaliber762NATOEffect",
        "add_ammo": "BPRUE_ChangeAmmoTypes762NATOEffect",
        "remove_ammo": [
            "ChangeAmmoTypesNo545Effect",
            "ChangeAmmoTypesNo556Effect",
            "BPRUE_ChangeAmmoTypesNo762Effect",
            "ChangeAmmoTypesNo939Effect",
        ],
    },
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def render_array(name: str, values: list[str], indent: str = "   ", bpatch: bool = False) -> list[str]:
    if not values:
        return []
    suffix = " {bpatch}" if bpatch else ""
    lines = [f"{indent}{name} : struct.begin{suffix}"]
    for index, value in enumerate(values):
        lines.append(f"{indent}   [{index}] = {value}")
    lines.append(f"{indent}struct.end")
    return lines


def module_template(family: dict) -> dict:
    modules = family.get("modules", [])
    if modules:
        return dict(modules[0])
    standard = family.get("standard_upgrades", [])
    if standard:
        return dict(standard[0])
    raise ValueError(f"No source upgrade available for {family['prototype_prefix']}")


def family_standard_upgrades(family_name: str, family: dict) -> list[dict]:
    # BPRUE currently uses the MODULES area for the experimental assault-rifle
    # specializations. The old fire-rate and reload tree nodes remain in the JSON
    # as source data / history, but are deliberately not emitted.
    return []


def make_power_caliber_module(family_name: str, family: dict) -> dict | None:
    if family_name in NINE_BY_THIRTY_NINE_FAMILIES:
        return None
    if family_name not in EASTERN_POWER_FAMILIES | WESTERN_POWER_FAMILIES:
        return None

    module = module_template(family)
    module.update({
        "kind": "caliber",
        "horizontal_position": 0,
        "vertical_position": "EUpgradeVerticalPosition::Top",
        "target_part": "EUpgradeTargetPartType::Body",
        "balance_class": "power",
    })

    prefix = family["prototype_prefix"]
    if family_name in EASTERN_POWER_FAMILIES:
        module.update({
            "sid": f"{prefix}_Upgrade_BPRUE_Caliber_762",
            "text_sid": "sid_bprue_caliber_762_eastern_name",
            "hint_sid": "sid_bprue_caliber_762_eastern_description",
            "caliber": "A762Sniper",
            "base_cost": 2800,
        })
    else:
        module.update({
            "sid": f"{prefix}_Upgrade_BPRUE_Caliber_762NATO",
            "text_sid": "sid_bprue_caliber_762_nato_name",
            "hint_sid": "sid_bprue_caliber_762_nato_description",
            "caliber": "A762NATO",
            "base_cost": 3200,
        })
    return module


def make_reload_modules(family: dict) -> list[dict]:
    template = module_template(family)
    prefix = family["prototype_prefix"]

    competition = dict(template)
    competition.update({
        "kind": "reload_competition",
        "sid": f"{prefix}_Upgrade_BPRUE_Reload_Competition",
        "text_sid": "sid_bprue_reload_competition_name",
        "hint_sid": "sid_bprue_reload_competition_description",
        "base_cost": 2800,
        "horizontal_position": 1,
        "vertical_position": "EUpgradeVerticalPosition::Down",
        "target_part": "EUpgradeTargetPartType::Body",
    })

    reinforced = dict(template)
    reinforced.update({
        "kind": "reload_reinforced",
        "sid": f"{prefix}_Upgrade_BPRUE_Reload_Reinforced",
        "text_sid": "sid_bprue_reload_reinforced_name",
        "hint_sid": "sid_bprue_reload_reinforced_description",
        "base_cost": 3000,
        "horizontal_position": 2,
        "vertical_position": "EUpgradeVerticalPosition::Down",
        "target_part": "EUpgradeTargetPartType::Body",
    })
    return [competition, reinforced]


def make_fire_rate_modules(family: dict) -> list[dict]:
    template = module_template(family)
    prefix = family["prototype_prefix"]

    high_speed = dict(template)
    high_speed.update({
        "kind": "fire_rate_high_speed",
        "sid": f"{prefix}_Upgrade_BPRUE_FireRate_HighSpeed",
        "text_sid": "sid_bprue_fire_rate_high_speed_name",
        "hint_sid": "sid_bprue_fire_rate_high_speed_description",
        "base_cost": 3400,
        "horizontal_position": 3,
        "vertical_position": "EUpgradeVerticalPosition::Top",
        "target_part": "EUpgradeTargetPartType::Barrel",
    })

    balanced = dict(template)
    balanced.update({
        "kind": "fire_rate_balanced",
        "sid": f"{prefix}_Upgrade_BPRUE_FireRate_Balanced",
        "text_sid": "sid_bprue_fire_rate_balanced_name",
        "hint_sid": "sid_bprue_fire_rate_balanced_description",
        "base_cost": 3200,
        "horizontal_position": 4,
        "vertical_position": "EUpgradeVerticalPosition::Top",
        "target_part": "EUpgradeTargetPartType::Barrel",
    })
    return [high_speed, balanced]


def make_fire_control_modules(family: dict) -> list[dict]:
    template = module_template(family)
    prefix = family["prototype_prefix"]

    burst = dict(template)
    burst.update({
        "kind": "fire_control_burst",
        "sid": f"{prefix}_Upgrade_BPRUE_FireControl_Burst",
        "text_sid": "sid_bprue_fire_control_burst_name",
        "hint_sid": "sid_bprue_fire_control_burst_description",
        "base_cost": 3000,
        "horizontal_position": 1,
        "vertical_position": "EUpgradeVerticalPosition::Top",
        "target_part": "EUpgradeTargetPartType::Body",
    })

    precision = dict(template)
    precision.update({
        "kind": "fire_control_precision",
        "sid": f"{prefix}_Upgrade_BPRUE_FireControl_Precision",
        "text_sid": "sid_bprue_fire_control_precision_name",
        "hint_sid": "sid_bprue_fire_control_precision_description",
        "base_cost": 3600,
        "horizontal_position": 2,
        "vertical_position": "EUpgradeVerticalPosition::Top",
        "target_part": "EUpgradeTargetPartType::Body",
    })
    return [burst, precision]


def family_modules(family_name: str, family: dict) -> list[dict]:
    result: list[dict] = []

    caliber_module = make_power_caliber_module(family_name, family)
    if caliber_module:
        result.append(caliber_module)

    result.extend(make_fire_control_modules(family))
    result.extend(make_fire_rate_modules(family))
    result.extend(make_reload_modules(family))
    return result


def all_upgrades(config: dict) -> list[dict]:
    result: list[dict] = []
    for family_name, family in config["families"].items():
        result.extend(family_standard_upgrades(family_name, family))
        result.extend(family_modules(family_name, family))
    return result


def caliber_module_effects(module: dict) -> list[str]:
    effects = CALIBER_EFFECTS[module["caliber"]]
    result = [effects["change"], *effects["remove_ammo"], effects["add_ammo"]]
    if module.get("balance_class") == "power":
        result += ["BPRUE_DamagePos10Effect", "RecoilNeg20Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    return result


def module_effects(module: dict) -> list[str]:
    kind = module.get("kind")
    if kind == "caliber":
        return caliber_module_effects(module)
    if kind == "reload_competition":
        return ["BPRUE_ReloadingTimeNeg20Effect", "RecoilNeg15Effect"]
    if kind == "reload_reinforced":
        return ["BPRUE_ReloadingTimeNeg10Effect", "DurabilityPerShotPos20Effect", "BPRUE_FireIntervalPos5Effect"]
    if kind == "fire_rate_high_speed":
        return ["BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    if kind == "fire_rate_balanced":
        return ["BPRUE_FireIntervalNeg10Effect", "RecoilPos10Effect", "BPRUE_DurabilityPerShotNeg10Effect"]
    if kind == "fire_control_burst":
        return ["BPRUE_AddBurstFireModeEffect", "RecoilPos5Effect", "BPRUE_DurabilityPerShotNeg10Effect"]
    if kind == "fire_control_precision":
        return ["BPRUE_SemiAutoOnlyEffect", "BPRUE_DamagePos10Effect", "ArmorPiercingPos15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    return module.get("effect_sids", [])


def module_group(kind: str | None) -> str | None:
    if kind in {"reload_competition", "reload_reinforced"}:
        return "reload"
    if kind in {"fire_rate_high_speed", "fire_rate_balanced"}:
        return "fire_rate"
    if kind in {"fire_control_burst", "fire_control_precision"}:
        return "fire_control"
    return kind


def render_upgrade(upgrade: dict, interchangeable: list[str] | None = None) -> str:
    kind = upgrade.get("kind")
    effects = module_effects(upgrade) if kind else upgrade.get("effect_sids", [])
    refkey = MODULE_TEMPLATE_SID if kind else UPGRADE_TEMPLATE_SID

    lines = [
        f"{upgrade['sid']} : struct.begin {{refkey={refkey}}}",
        f"   SID = {upgrade['sid']}",
        f"   Text = {upgrade['text_sid']}",
        f"   Hint = {upgrade['hint_sid']}",
        f"   Image = {upgrade['image']}",
        f"   Icon = {upgrade['icon']}",
        f"   BaseCost = {upgrade['base_cost']}",
        f"   HorizontalPosition = {upgrade['horizontal_position']}",
        f"   VerticalPosition = {upgrade['vertical_position']}",
        f"   UpgradeTargetPart = {upgrade['target_part']}",
    ]
    lines += render_array("EffectPrototypeSIDs", effects)
    if interchangeable:
        lines += render_array("InterchangeableUpgradePrototypeSIDs", interchangeable)
    lines.append("struct.end")
    return "\n".join(lines)


def render_upgrade_patch(config: dict) -> str:
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "//",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json",
        "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------",
        "",
        "// Assault-rifle BPRUE extensions are currently modeled as technician modules.",
        "// Module groups are internally interchangeable: reload, fire-rate and fire-control.",
        "// Caliber conversions remain faction-family coherent (Eastern / Western).",
        "",
        f"{UPGRADE_TEMPLATE_SID} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}",
        f"   SID = {UPGRADE_TEMPLATE_SID}",
        "struct.end",
        "",
        f"{MODULE_TEMPLATE_SID} : struct.begin {{refkey={UPGRADE_TEMPLATE_SID}}}",
        f"   SID = {MODULE_TEMPLATE_SID}",
        "   IsModification = true",
        "struct.end",
        "",
    ]

    for family_name, family in config["families"].items():
        lines.append(f"// --- {family_name} ------------------------------------------------------------")
        modules = family_modules(family_name, family)
        for module in modules:
            group = module_group(module.get("kind"))
            interchangeable = [
                other["sid"]
                for other in modules
                if other["sid"] != module["sid"] and module_group(other.get("kind")) == group
            ]
            lines.append(render_upgrade(module, interchangeable or None))
            lines.append("")
    return "\n".join(lines)


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
   LocalizationSID = bprue_fire_modes
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


def render_weapon_patch(config: dict) -> str:
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json",
        "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for family_name, family in config["families"].items():
        modules = family_modules(family_name, family)
        lines += [f"// {family_name}", f"{family['weapon_sid']} : struct.begin {{bpatch}}"]
        if any(module.get("kind") == "fire_control_burst" for module in modules):
            lines.append(f"   FireQueueCount = {family.get('fire_queue_count', 3)}")
        lines.append("   UpgradePrototypeSIDs : struct.begin {bpatch}")
        for upgrade in modules:
            lines.append(f"      {upgrade['sid']} = {upgrade['sid']}")
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def render_appended_upgrade_entries(upgrades: list[dict], indent: str = "      ") -> list[str]:
    lines: list[str] = []
    for upgrade in upgrades:
        lines += [
            f"{indent}[*] : struct.begin",
            f"{indent}   UpgradePrototypeSID = {upgrade['sid']}",
            f"{indent}   Enabled = true",
            f"{indent}struct.end",
        ]
    return lines


def render_npc_patch(config: dict) -> str:
    technician = config["technician"]
    upgrades = all_upgrades(config)
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json",
        "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------",
        "",
        "// Draft setup: all BPRUE assault-rifle modules are available at all technicians.",
        "",
    ]
    prototype_sids = [
        technician["prototype_sid"],
        technician["all_prototype_sid"],
        *technician.get("concrete_prototype_sids", []),
    ]
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
    outputs = {
        UPGRADE_OUTPUT_PATH: render_upgrade_patch(config),
        EFFECT_OUTPUT_PATH: render_effect_patch(config),
        WEAPON_OUTPUT_PATH: render_weapon_patch(config),
        NPC_OUTPUT_PATH: render_npc_patch(config),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
