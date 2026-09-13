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
    "A545": {
        "change": "ChangeCaliber545Effect",
        "add_ammo": "ChangeAmmoTypes545Effect",
        "remove_ammo": ["ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "BPRUE_ChangeAmmoTypesNo762NATOEffect", "ChangeAmmoTypesNo939Effect"],
    },
    "A556": {
        "change": "ChangeCaliber556Effect",
        "add_ammo": "ChangeAmmoTypes556Effect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "BPRUE_ChangeAmmoTypesNo762NATOEffect", "ChangeAmmoTypesNo939Effect"],
    },
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
    "A939": {
        "change": "BPRUE_ChangeCaliber939Effect",
        "add_ammo": "ChangeAmmoTypes939Effect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "BPRUE_ChangeAmmoTypesNo762NATOEffect"],
    },
}

# Only the first fire-rate tier anchors into the existing vanilla tree.
# Fire-rate H2/H3 then continue the BPRUE row at horizontal positions 2 and 3.
STANDARD_UPGRADE_PARENTS = {
    "GunAK74_Upgrade_BPRUE_FireRate": "GunAK74_Upgrade_Barrel_2_1",
    "GunFora_Upgrade_BPRUE_FireRate": "GunFora_Upgrade_Barrel_3",
    "GunG37_Upgrade_BPRUE_FireRate": "GunG37_Upgrade_Barrel_2_1",
    "GunGvintar_Upgrade_BPRUE_FireRate": "GunGvintar_Upgrade_Barrel_3",
    "GunM16_Upgrade_BPRUE_FireRate": "GunM16_Upgrade_Barrel_3",
    "GunGrim_Upgrade_BPRUE_FireRate": "GunGrim_Upgrade_Barrel_2",
    "GunLavina_Upgrade_BPRUE_FireRate": "GunLavina_Upgrade_Barrel_3",
    "GunDnipro_Upgrade_BPRUE_FireRate": "GunDnipro_Upgrade_Barrel_3",
    "GunKharod_Upgrade_BPRUE_FireRate": "GunKharod_Upgrade_Barrel_3_1",
    "GunArev_Upgrade_BPRUE_FireRate": "GunArev_Upgrade_Barrel_3_1",
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


def fire_rate_tier_upgrades(fire_rate: dict) -> list[dict]:
    result: list[dict] = []
    for suffix, cost_add in [("_H2", 800), ("_H3", 1600)]:
        upgrade = dict(fire_rate)
        upgrade["sid"] = f"{fire_rate['sid']}{suffix}"
        upgrade["base_cost"] = fire_rate["base_cost"] + cost_add
        result.append(upgrade)
    return result


def family_standard_upgrades(family_name: str, family: dict) -> list[dict]:
    result: list[dict] = []
    for upgrade in family.get("standard_upgrades", []):
        # Reload specialization now lives in MODULES instead of the normal tree.
        if upgrade["sid"].endswith("_BPRUE_Reload"):
            continue
        result.append(upgrade)
        if upgrade["sid"].endswith("_BPRUE_FireRate"):
            result.extend(fire_rate_tier_upgrades(upgrade))
    return result


def module_template(family: dict) -> dict:
    modules = family.get("modules", [])
    if modules:
        return dict(modules[0])
    standard = family.get("standard_upgrades", [])
    if standard:
        return dict(standard[0])
    raise ValueError(f"No source upgrade available for {family['prototype_prefix']}")


def make_power_caliber_module(family_name: str, family: dict) -> dict | None:
    if family_name in NINE_BY_THIRTY_NINE_FAMILIES:
        return None
    if family_name not in EASTERN_POWER_FAMILIES | WESTERN_POWER_FAMILIES:
        return None

    module = module_template(family)
    module["kind"] = "caliber"
    module["horizontal_position"] = 0
    module["vertical_position"] = "EUpgradeVerticalPosition::Top"
    module["target_part"] = "EUpgradeTargetPartType::Body"
    module["base_cost"] = 3200 if family_name in WESTERN_POWER_FAMILIES else 2800
    module["balance_class"] = "power"

    prefix = family["prototype_prefix"]
    if family_name in EASTERN_POWER_FAMILIES:
        module["sid"] = f"{prefix}_Upgrade_BPRUE_Caliber_762"
        module["text_sid"] = "sid_bprue_caliber_762_eastern_name"
        module["hint_sid"] = "sid_bprue_caliber_762_eastern_description"
        module["caliber"] = "A762Sniper"
    else:
        module["sid"] = f"{prefix}_Upgrade_BPRUE_Caliber_762NATO"
        module["text_sid"] = "sid_bprue_caliber_762_nato_name"
        module["hint_sid"] = "sid_bprue_caliber_762_nato_description"
        module["caliber"] = "A762NATO"

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


def family_modules(family_name: str, family: dict) -> list[dict]:
    result: list[dict] = []

    caliber_module = make_power_caliber_module(family_name, family)
    if caliber_module:
        result.append(caliber_module)

    # Keep fire-mode modules from the source config, but discard the old cross-family caliber draft.
    result.extend(module for module in family.get("modules", []) if module.get("kind") == "burst")
    result.extend(make_reload_modules(family))
    return result


def all_upgrades(config: dict) -> list[dict]:
    result: list[dict] = []
    for family_name, family in config["families"].items():
        result.extend(family_standard_upgrades(family_name, family))
        result.extend(family_modules(family_name, family))
    return result


def caliber_module_effects(module: dict, family: dict) -> list[str]:
    effects = CALIBER_EFFECTS[module["caliber"]]
    result = [effects["change"], *effects["remove_ammo"], effects["add_ammo"]]

    if module.get("balance_class") == "power":
        result += ["BPRUE_DamagePos10Effect", "RecoilNeg20Effect", "BPRUE_DurabilityPerShotNeg20Effect"]

    return result


def module_effects(module: dict, family: dict) -> list[str]:
    kind = module.get("kind")
    if kind == "caliber":
        return caliber_module_effects(module, family)
    if kind == "burst":
        return ["BPRUE_AddBurstFireModeEffect"]
    if kind == "reload_competition":
        return ["BPRUE_ReloadingTimeNeg20Effect", "RecoilNeg15Effect"]
    if kind == "reload_reinforced":
        return ["BPRUE_ReloadingTimeNeg10Effect", "DurabilityPerShotPos20Effect", "BPRUE_FireIntervalPos5Effect"]
    return module.get("effect_sids", [])


def standard_upgrade_layout(upgrade: dict) -> tuple[str, str, int] | None:
    sid = upgrade["sid"]

    if sid.endswith("_BPRUE_FireRate_H2"):
        previous_sid = sid[:-3]
        return previous_sid, previous_sid, 2

    if sid.endswith("_BPRUE_FireRate_H3"):
        base_sid = sid[:-3]
        previous_sid = f"{base_sid}_H2"
        return previous_sid, previous_sid, 3

    parent_sid = STANDARD_UPGRADE_PARENTS.get(sid)
    if parent_sid:
        return parent_sid, parent_sid, 1

    return None


def render_upgrade(upgrade: dict, family: dict, interchangeable: list[str] | None = None) -> str:
    kind = upgrade.get("kind")
    effects = module_effects(upgrade, family) if kind else upgrade.get("effect_sids", [])

    refkey = MODULE_TEMPLATE_SID if kind else UPGRADE_TEMPLATE_SID
    ref_suffix = ""
    horizontal_position = upgrade["horizontal_position"]
    required_upgrade_sids: list[str] = []
    connection_lines: list[str] = []

    if kind is None:
        layout = standard_upgrade_layout(upgrade)
        if layout:
            refkey, required_sid, horizontal_position = layout
            ref_suffix = ";bpatch"
            required_upgrade_sids = [required_sid]
            connection_lines = [
                "EConnectionLineState::Down"
                if upgrade["vertical_position"] == "EUpgradeVerticalPosition::Top"
                else "EConnectionLineState::Top"
            ]

    lines = [
        f"{upgrade['sid']} : struct.begin {{refkey={refkey}{ref_suffix}}}",
        f"   SID = {upgrade['sid']}",
        f"   Text = {upgrade['text_sid']}",
        f"   Hint = {upgrade['hint_sid']}",
        f"   Image = {upgrade['image']}",
        f"   Icon = {upgrade['icon']}",
        f"   BaseCost = {upgrade['base_cost']}",
        f"   HorizontalPosition = {horizontal_position}",
        f"   VerticalPosition = {upgrade['vertical_position']}",
        f"   UpgradeTargetPart = {upgrade['target_part']}",
    ]
    lines += render_array("EffectPrototypeSIDs", effects, bpatch=kind is None)
    if required_upgrade_sids:
        lines += render_array("RequiredUpgradePrototypeSIDs", required_upgrade_sids)
        lines += render_array("ConnectionLines", connection_lines)
    if interchangeable:
        lines += render_array("InterchangeableUpgradePrototypeSIDs", interchangeable)
    lines.append("struct.end")
    return "\n".join(lines)


def render_upgrade_patch(config: dict) -> str:
    lines = [
        "// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "//",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json", "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------", "",
        "// UPGRADES: three-stage fire-rate progression.",
        "// MODULES: power-caliber conversions, fire-mode conversions and reload specializations.",
        "// 5.45/5.56 cross-family caliber conversions are deliberately excluded.", "",
        f"{UPGRADE_TEMPLATE_SID} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}", f"   SID = {UPGRADE_TEMPLATE_SID}", "struct.end", "",
        f"{MODULE_TEMPLATE_SID} : struct.begin {{refkey={UPGRADE_TEMPLATE_SID}}}", f"   SID = {MODULE_TEMPLATE_SID}", "   IsModification = true", "struct.end", "",
    ]

    for family_name, family in config["families"].items():
        lines.append(f"// --- {family_name} ------------------------------------------------------------")
        for upgrade in family_standard_upgrades(family_name, family):
            lines.append(render_upgrade(upgrade, family))
            lines.append("")

        modules = family_modules(family_name, family)
        for module in modules:
            kind = module.get("kind")
            group = "reload" if kind in {"reload_competition", "reload_reinforced"} else kind
            interchangeable = [
                other["sid"]
                for other in modules
                if other["sid"] != module["sid"]
                and ("reload" if other.get("kind") in {"reload_competition", "reload_reinforced"} else other.get("kind")) == group
            ]
            lines.append(render_upgrade(module, family, interchangeable or None))
            lines.append("")

    return "\n".join(lines)


def render_effect_patch(config: dict) -> str:
    fire_interval = config["shared_balance"]["fire_interval_percent"]
    return f"""// -----------------------------------------------------------------------------
// AUTO-GENERATED FILE - DO NOT EDIT BY HAND
// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json
// Generated by: generate_assault_rifle_upgrades.py
// -----------------------------------------------------------------------------

BPRUE_FireIntervalNeg10Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}
   SID = BPRUE_FireIntervalNeg10Effect
   Text = Increase Fire Rate
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = {fire_interval}%
   ValueMax = {fire_interval}%
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end

BPRUE_FireIntervalPos5Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}
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

BPRUE_DamagePos10Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DamageTemplate}}
   SID = BPRUE_DamagePos10Effect
   ValueMin = 10%
   ValueMax = 10%
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg20Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}}
   SID = BPRUE_DurabilityPerShotNeg20Effect
   ValueMin = 20%
   ValueMax = 20%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_ReloadingTimeNeg20Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}
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

BPRUE_ReloadingTimeNeg10Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}
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

BPRUE_AddBurstFireModeEffect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeFireTypeTemplate}}
   SID = BPRUE_AddBurstFireModeEffect
   LocalizationSID = bprue_fire_modes
   FireTypes : struct.begin
      [0] = EFireType::SemiAutomatic
      [1] = EFireType::Queue
      [2] = EFireType::Automatic
   struct.end
   ShowUpgradeEffectValue = false
struct.end

BPRUE_ChangeCaliber939Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeCaliberTemplate}}
   SID = BPRUE_ChangeCaliber939Effect
   Caliber = EAmmoCaliber::A939
   ShowUpgradeEffectValue = false
struct.end

BPRUE_ChangeCaliber762NATOEffect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeCaliberTemplate}}
   SID = BPRUE_ChangeCaliber762NATOEffect
   Caliber = EAmmoCaliber::A762NATO
   ShowUpgradeEffectValue = false
struct.end

BPRUE_ChangeAmmoTypes762NATOEffect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}}
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

BPRUE_ChangeAmmoTypesNo762NATOEffect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}}
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

BPRUE_ChangeAmmoTypesNo762Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}}
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
        "// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json", "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------", "",
    ]
    for family_name, family in config["families"].items():
        modules = family_modules(family_name, family)
        upgrades = [*family_standard_upgrades(family_name, family), *modules]
        lines += [f"// {family_name}", f"{family['weapon_sid']} : struct.begin {{bpatch}}"]
        if any(module.get("kind") == "burst" for module in modules):
            lines.append(f"   FireQueueCount = {family.get('fire_queue_count', 3)}")
        lines.append("   UpgradePrototypeSIDs : struct.begin {bpatch}")
        for upgrade in upgrades:
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
        "// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json", "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------", "", "// Draft setup: all BPRUE assault-rifle upgrades are available at all technicians.", "",
    ]
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
