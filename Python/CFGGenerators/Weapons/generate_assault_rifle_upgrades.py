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

CALIBER_EFFECTS = {
    "A545": {
        "change": "ChangeCaliber545Effect",
        "add_ammo": "ChangeAmmoTypes545Effect",
        "remove_ammo": ["ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"],
    },
    "A556": {
        "change": "ChangeCaliber556Effect",
        "add_ammo": "ChangeAmmoTypes556Effect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"],
    },
    "A762Sniper": {
        "change": "ChangeCaliber762Effect",
        "add_ammo": "ChangeAmmoTypes762Effect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "ChangeAmmoTypesNo939Effect"],
    },
    "A939": {
        "change": "BPRUE_ChangeCaliber939Effect",
        "add_ammo": "ChangeAmmoTypes939Effect",
        "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect"],
    },
}

# DurabilityTiers establishes the working pattern for extending a normal upgrade tree:
# each new node sits one horizontal slot after an existing node, requires that node,
# and renders a connection line back to it. Keep modules independent.
STANDARD_UPGRADE_CONNECTIONS = {
    "GunAK74_Upgrade_BPRUE_FireRate": ("GunAK74_Upgrade_Barrel_2_1", 2),
    "GunAK74_Upgrade_BPRUE_Reload": ("GunAK74_Upgrade_Body_2", 2),
    "GunFora_Upgrade_BPRUE_FireRate": ("GunFora_Upgrade_Barrel_3", 3),
    "GunFora_Upgrade_BPRUE_Reload": ("GunFora_Upgrade_Body_3_2", 3),
    "GunG37_Upgrade_BPRUE_FireRate": ("GunG37_Upgrade_Barrel_2_1", 2),
    "GunG37_Upgrade_BPRUE_Reload": ("GunG37_Upgrade_Body_1_2", 1),
    "GunGvintar_Upgrade_BPRUE_FireRate": ("GunGvintar_Upgrade_Barrel_3", 3),
    "GunGvintar_Upgrade_BPRUE_Reload": ("GunGvintar_Upgrade_Body_3", 3),
    "GunM16_Upgrade_BPRUE_FireRate": ("GunM16_Upgrade_Barrel_3", 3),
    "GunM16_Upgrade_BPRUE_Reload": ("GunM16_Upgrade_Body_1", 1),
    "GunGrim_Upgrade_BPRUE_FireRate": ("GunGrim_Upgrade_Barrel_2", 2),
    "GunGrim_Upgrade_BPRUE_Reload": ("GunGrim_Upgrade_Body_3_2", 3),
    "GunLavina_Upgrade_BPRUE_FireRate": ("GunLavina_Upgrade_Barrel_3", 3),
    "GunLavina_Upgrade_BPRUE_Reload": ("GunLavina_Upgrade_Body_3", 3),
    "GunDnipro_Upgrade_BPRUE_FireRate": ("GunDnipro_Upgrade_Barrel_3", 3),
    "GunDnipro_Upgrade_BPRUE_Reload": ("GunDnipro_Upgrade_Body_2", 2),
    "GunKharod_Upgrade_BPRUE_FireRate": ("GunKharod_Upgrade_Barrel_3_1", 3),
    "GunKharod_Upgrade_BPRUE_Reload": ("GunKharod_Upgrade_Body_1", 1),
    "GunArev_Upgrade_BPRUE_FireRate": ("GunArev_Upgrade_Barrel_3_1", 3),
    "GunArev_Upgrade_BPRUE_Reload": ("GunArev_Upgrade_Body_3", 3),
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


def all_upgrades(config: dict) -> list[dict]:
    result: list[dict] = []
    for family in config["families"].values():
        result.extend(family.get("standard_upgrades", []))
        result.extend(family.get("modules", []))
    return result


def caliber_module_effects(module: dict) -> list[str]:
    caliber = module["caliber"]
    effects = CALIBER_EFFECTS[caliber]
    result = [effects["change"], *effects["remove_ammo"], effects["add_ammo"]]
    balance_class = module.get("balance_class")
    if balance_class == "power":
        result += ["BPRUE_DamagePos10Effect", "BPRUE_DurabilityPerShotNeg20Effect"]
    elif balance_class == "economy":
        result += ["BPRUE_DamageNeg10Effect", "BPRUE_DurabilityPerShotPos20Effect", "RecoilPos10Effect"]
    return result


def render_upgrade(upgrade: dict, interchangeable: list[str] | None = None) -> str:
    effects = upgrade.get("effect_sids", [])
    kind = upgrade.get("kind")
    if kind == "caliber":
        effects = caliber_module_effects(upgrade)
    elif kind == "burst":
        effects = ["BPRUE_AddBurstFireModeEffect"]

    refkey = MODULE_TEMPLATE_SID if kind in {"caliber", "burst"} else UPGRADE_TEMPLATE_SID
    horizontal_position = upgrade["horizontal_position"]
    required_upgrade_sids: list[str] = []
    connection_lines: list[str] = []

    if kind is None and upgrade["sid"] in STANDARD_UPGRADE_CONNECTIONS:
        parent_sid, horizontal_position = STANDARD_UPGRADE_CONNECTIONS[upgrade["sid"]]
        required_upgrade_sids = [parent_sid]
        connection_lines = ["EConnectionLineState::Top"]

    lines = [
        f"{upgrade['sid']} : struct.begin {{refkey={refkey}}}",
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
    lines += render_array("EffectPrototypeSIDs", effects)

    if required_upgrade_sids:
        lines += render_array("RequiredUpgradePrototypeSIDs", required_upgrade_sids)
        lines += render_array("ConnectionLines", connection_lines)

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
        "// BPRUE master templates: inherit explicitly from the vanilla UpgradePrototypes",
        "// base template, then keep all generated upgrades on BPRUE-owned references.",
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
        "// First assault-rifle-family expansion draft.",
        "// Normal upgrades extend existing vanilla trees using the DurabilityTiers pattern:",
        "// RequiredUpgradePrototypeSIDs + ConnectionLines + the next horizontal slot.",
        "// Caliber and burst conversions remain independent technician modules.",
        "",
    ]

    for family_name, family in config["families"].items():
        lines.append(f"// --- {family_name} ------------------------------------------------------------")
        for upgrade in family.get("standard_upgrades", []):
            lines.append(render_upgrade(upgrade))
            lines.append("")

        caliber_modules = [m for m in family.get("modules", []) if m.get("kind") == "caliber"]
        caliber_sids = [m["sid"] for m in caliber_modules]
        for module in family.get("modules", []):
            interchangeable = None
            if module.get("kind") == "caliber":
                interchangeable = [sid for sid in caliber_sids if sid != module["sid"]]
            lines.append(render_upgrade(module, interchangeable))
            lines.append("")

    return "\n".join(lines)


def render_effect_patch(config: dict) -> str:
    fire_interval = config["shared_balance"]["fire_interval_percent"]
    reload_time = config["shared_balance"]["reload_time_percent"]

    return f"""// -----------------------------------------------------------------------------
// AUTO-GENERATED FILE - DO NOT EDIT BY HAND
//
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

BPRUE_DamagePos10Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DamageTemplate}}
   SID = BPRUE_DamagePos10Effect
   ValueMin = 10%
   ValueMax = 10%
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_DurabilityPerShotNeg20Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}}
   SID = BPRUE_DurabilityPerShotNeg20Effect
   ValueMin = 20%
   ValueMax = 20%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = false
   ShowUpgradeEffect = false
struct.end

BPRUE_ReloadingTimeNeg15Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}
   SID = BPRUE_ReloadingTimeNeg15Effect
   Text = Decrease Reloading Time
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = {reload_time}%
   ValueMax = {reload_time}%
   bIsPermanent = true
   Positive = EBeneficial::Positive
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

// Vanilla has ChangeCaliber effects for 5.45, 5.56 and 7.62 Sniper but not 9x39.
BPRUE_ChangeCaliber939Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeCaliberTemplate}}
   SID = BPRUE_ChangeCaliber939Effect
   Caliber = EAmmoCaliber::A939
   ShowUpgradeEffectValue = false
struct.end

// Vanilla exposes ChangeAmmoTypes762Effect but no complete matching remove effect.
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
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "//",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json",
        "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------",
        "",
    ]

    for family_name, family in config["families"].items():
        upgrades = [*family.get("standard_upgrades", []), *family.get("modules", [])]
        lines += [
            f"// {family_name}",
            f"{family['weapon_sid']} : struct.begin {{bpatch}}",
        ]
        if any(module.get("kind") == "burst" for module in family.get("modules", [])):
            lines.append(f"   FireQueueCount = {family.get('fire_queue_count', 3)}")
        lines.append("   UpgradePrototypeSIDs : struct.begin {bpatch}")
        for upgrade in upgrades:
            lines.append(f"      {upgrade['sid']} = {upgrade['sid']}")
        lines += [
            "   struct.end",
            "struct.end",
            "",
        ]

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
        "//",
        "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json",
        "// Generated by: generate_assault_rifle_upgrades.py",
        "// -----------------------------------------------------------------------------",
        "",
        "// Draft setup: all BPRUE assault-rifle upgrades are available at all technicians.",
        "// Technician progression can be restricted after the family designs are finalized.",
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
        lines += [
            f"{prototype_sid} : struct.begin {{bpatch}}",
            "   Upgrades : struct.begin {bpatch}",
        ]
        lines += render_appended_upgrade_entries(upgrades)
        lines += [
            "   struct.end",
            "struct.end",
            "",
        ]

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
