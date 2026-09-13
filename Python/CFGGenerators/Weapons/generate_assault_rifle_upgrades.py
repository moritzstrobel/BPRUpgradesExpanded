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
    "A545": {"change": "ChangeCaliber545Effect", "add_ammo": "ChangeAmmoTypes545Effect", "remove_ammo": ["ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"]},
    "A556": {"change": "ChangeCaliber556Effect", "add_ammo": "ChangeAmmoTypes556Effect", "remove_ammo": ["ChangeAmmoTypesNo545Effect", "BPRUE_ChangeAmmoTypesNo762Effect", "ChangeAmmoTypesNo939Effect"]},
    "A762Sniper": {"change": "ChangeCaliber762Effect", "add_ammo": "ChangeAmmoTypes762Effect", "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "ChangeAmmoTypesNo939Effect"]},
    "A939": {"change": "BPRUE_ChangeCaliber939Effect", "add_ammo": "ChangeAmmoTypes939Effect", "remove_ammo": ["ChangeAmmoTypesNo545Effect", "ChangeAmmoTypesNo556Effect", "BPRUE_ChangeAmmoTypesNo762Effect"]},
}

# First fire-rate tier / reload node anchors into the existing vanilla tree.
# Fire-rate H2/H3 then continue the BPRUE row at horizontal positions 2 and 3.
STANDARD_UPGRADE_PARENTS = {
    "GunAK74_Upgrade_BPRUE_FireRate": "GunAK74_Upgrade_Barrel_2_1",
    "GunAK74_Upgrade_BPRUE_Reload": "GunAK74_Upgrade_Body_2",
    "GunFora_Upgrade_BPRUE_FireRate": "GunFora_Upgrade_Barrel_3",
    "GunFora_Upgrade_BPRUE_Reload": "GunFora_Upgrade_Body_3_2",
    "GunG37_Upgrade_BPRUE_FireRate": "GunG37_Upgrade_Barrel_2_1",
    "GunG37_Upgrade_BPRUE_Reload": "GunG37_Upgrade_Body_1_2",
    "GunGvintar_Upgrade_BPRUE_FireRate": "GunGvintar_Upgrade_Barrel_3",
    "GunGvintar_Upgrade_BPRUE_Reload": "GunGvintar_Upgrade_Body_3",
    "GunM16_Upgrade_BPRUE_FireRate": "GunM16_Upgrade_Barrel_3",
    "GunM16_Upgrade_BPRUE_Reload": "GunM16_Upgrade_Body_1",
    "GunGrim_Upgrade_BPRUE_FireRate": "GunGrim_Upgrade_Barrel_2",
    "GunGrim_Upgrade_BPRUE_Reload": "GunGrim_Upgrade_Body_3_2",
    "GunLavina_Upgrade_BPRUE_FireRate": "GunLavina_Upgrade_Barrel_3",
    "GunLavina_Upgrade_BPRUE_Reload": "GunLavina_Upgrade_Body_3",
    "GunDnipro_Upgrade_BPRUE_FireRate": "GunDnipro_Upgrade_Barrel_3",
    "GunDnipro_Upgrade_BPRUE_Reload": "GunDnipro_Upgrade_Body_2",
    "GunKharod_Upgrade_BPRUE_FireRate": "GunKharod_Upgrade_Barrel_3_1",
    "GunKharod_Upgrade_BPRUE_Reload": "GunKharod_Upgrade_Body_1",
    "GunArev_Upgrade_BPRUE_FireRate": "GunArev_Upgrade_Barrel_3_1",
    "GunArev_Upgrade_BPRUE_Reload": "GunArev_Upgrade_Body_3",
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
        # Reuse the same localization for now; the three stages are primarily
        # a progression/layout mechanic and each stage adds another +10% fire rate.
        upgrade["base_cost"] = fire_rate["base_cost"] + cost_add
        result.append(upgrade)
    return result


def family_standard_upgrades(family_name: str, family: dict) -> list[dict]:
    result: list[dict] = []
    for upgrade in family.get("standard_upgrades", []):
        result.append(upgrade)
        if upgrade["sid"].endswith("_BPRUE_FireRate"):
            result.extend(fire_rate_tier_upgrades(upgrade))
    return result


def all_upgrades(config: dict) -> list[dict]:
    result: list[dict] = []
    for family_name, family in config["families"].items():
        result.extend(family_standard_upgrades(family_name, family))
        result.extend(family.get("modules", []))
    return result


def caliber_balance_class(module: dict, family: dict) -> str:
    target_caliber = module["caliber"]
    base_caliber = family.get("base_caliber")

    # Re-selecting the weapon's native caliber should only restore the base
    # ammunition setup; it must not grant a free stat package.
    if target_caliber == base_caliber:
        return "neutral"

    if target_caliber == "A762Sniper":
        return "power"

    if base_caliber == "A545" and target_caliber == "A556":
        return "performance"

    if base_caliber == "A556" and target_caliber == "A545":
        return "economy"

    return module.get("balance_class", "lateral")


def caliber_module_effects(module: dict, family: dict) -> list[str]:
    effects = CALIBER_EFFECTS[module["caliber"]]
    result = [effects["change"], *effects["remove_ammo"], effects["add_ammo"]]
    balance_class = caliber_balance_class(module, family)

    if balance_class == "performance":
        # 5.45 -> 5.56: more punch, paid for with recoil and wear.
        result += ["BPRUE_DamagePos10Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg10Effect"]
    elif balance_class == "economy":
        # 5.56 -> 5.45: less punch, but softer recoil and lower weapon wear.
        result += ["DamageNeg10Effect", "RecoilPos10Effect", "DurabilityPerShotPos20Effect"]
    elif balance_class == "power":
        # High-power 7.62 Sniper conversion: strong damage increase with a
        # noticeably harsher recoil impulse and accelerated wear.
        result += ["BPRUE_DamagePos10Effect", "RecoilNeg20Effect", "BPRUE_DurabilityPerShotNeg20Effect"]

    return result


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
    effects = upgrade.get("effect_sids", [])
    kind = upgrade.get("kind")
    if kind == "caliber":
        effects = caliber_module_effects(upgrade, family)
    elif kind == "burst":
        effects = ["BPRUE_AddBurstFireModeEffect"]

    refkey = MODULE_TEMPLATE_SID if kind in {"caliber", "burst"} else UPGRADE_TEMPLATE_SID
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
        "// BPRUE master templates are kept for independent modules.",
        "// Standard upgrades follow the working DurabilityTiers extension pattern.",
        "// Every assault rifle receives a three-stage +10% fire-rate progression.", "",
        f"{UPGRADE_TEMPLATE_SID} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}", f"   SID = {UPGRADE_TEMPLATE_SID}", "struct.end", "",
        f"{MODULE_TEMPLATE_SID} : struct.begin {{refkey={UPGRADE_TEMPLATE_SID}}}", f"   SID = {MODULE_TEMPLATE_SID}", "   IsModification = true", "struct.end", "",
    ]
    for family_name, family in config["families"].items():
        lines.append(f"// --- {family_name} ------------------------------------------------------------")
        for upgrade in family_standard_upgrades(family_name, family):
            lines.append(render_upgrade(upgrade, family)); lines.append("")
        caliber_modules = [m for m in family.get("modules", []) if m.get("kind") == "caliber"]
        caliber_sids = [m["sid"] for m in caliber_modules]
        for module in family.get("modules", []):
            interchangeable = [sid for sid in caliber_sids if sid != module["sid"]] if module.get("kind") == "caliber" else None
            lines.append(render_upgrade(module, family, interchangeable)); lines.append("")
    return "\n".join(lines)


def render_effect_patch(config: dict) -> str:
    fire_interval = config["shared_balance"]["fire_interval_percent"]
    reload_time = config["shared_balance"]["reload_time_percent"]
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

BPRUE_DamagePos10Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DamageTemplate}}
   SID = BPRUE_DamagePos10Effect
   ValueMin = 10%
   ValueMax = 10%
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end

BPRUE_DurabilityPerShotNeg10Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}}
   SID = BPRUE_DurabilityPerShotNeg10Effect
   ValueMin = 10%
   ValueMax = 10%
   Positive = EBeneficial::Negative
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

BPRUE_ChangeCaliber939Effect : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeCaliberTemplate}}
   SID = BPRUE_ChangeCaliber939Effect
   Caliber = EAmmoCaliber::A939
   ShowUpgradeEffectValue = false
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
    lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json", "// Generated by: generate_assault_rifle_upgrades.py", "// -----------------------------------------------------------------------------", ""]
    for family_name, family in config["families"].items():
        upgrades = [*family_standard_upgrades(family_name, family), *family.get("modules", [])]
        lines += [f"// {family_name}", f"{family['weapon_sid']} : struct.begin {{bpatch}}"]
        if any(module.get("kind") == "burst" for module in family.get("modules", [])):
            lines.append(f"   FireQueueCount = {family.get('fire_queue_count', 3)}")
        lines.append("   UpgradePrototypeSIDs : struct.begin {bpatch}")
        for upgrade in upgrades:
            lines.append(f"      {upgrade['sid']} = {upgrade['sid']}")
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def render_appended_upgrade_entries(upgrades: list[dict], indent: str = "      ") -> list[str]:
    lines: list[str] = []
    for upgrade in upgrades:
        lines += [f"{indent}[*] : struct.begin", f"{indent}   UpgradePrototypeSID = {upgrade['sid']}", f"{indent}   Enabled = true", f"{indent}struct.end"]
    return lines


def render_npc_patch(config: dict) -> str:
    technician = config["technician"]
    upgrades = all_upgrades(config)
    lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// Source: Python/CFGGenerators/Weapons/assault_rifles_upgrades.json", "// Generated by: generate_assault_rifle_upgrades.py", "// -----------------------------------------------------------------------------", "", "// Draft setup: all BPRUE assault-rifle upgrades are available at all technicians.", ""]
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
    outputs = {UPGRADE_OUTPUT_PATH: render_upgrade_patch(config), EFFECT_OUTPUT_PATH: render_effect_patch(config), WEAPON_OUTPUT_PATH: render_weapon_patch(config), NPC_OUTPUT_PATH: render_npc_patch(config)}
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
