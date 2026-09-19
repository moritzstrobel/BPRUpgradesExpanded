from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition

CONFIG_PATH = Path(__file__).with_name("dlc_weapons.json")
SIGNATURE_CONFIG_PATH = Path(__file__).with_name("dlc_signatures.json")

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


def load_dlc_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_dlc_signature_config() -> dict:
    return json.loads(SIGNATURE_CONFIG_PATH.read_text(encoding="utf-8"))


def _dlc_prefix(pack: str, name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", f"{pack}{name}")
    return f"BPRUEDLC{token}"


def _clone_sid(source_sid: str, base_prefix: str, dlc_prefix: str) -> str:
    if not source_sid.startswith(base_prefix):
        raise ValueError(f"Cannot clone {source_sid}: expected base prefix {base_prefix}")
    return dlc_prefix + source_sid[len(base_prefix):]


def _add_dlc_signatures(result: dict[str, UpgradeBuildModel], weapons: dict) -> int:
    signatures = load_dlc_signature_config().get("signatures", {})
    unknown = sorted(set(signatures) - set(weapons))
    if unknown:
        raise ValueError("DLC signatures reference unknown weapons: " + ", ".join(unknown))

    added = 0
    for name, signature in signatures.items():
        weapon = weapons[name]
        pack = weapon["content_pack"]
        weapon_class = WEAPON_CLASS_CODES.get(weapon["class"])
        if not weapon_class:
            raise ValueError(f"{pack}/{name}: unsupported DLC signature class {weapon['class']}")
        token = re.sub(r"[^A-Za-z0-9]", "", name)
        key_token = "".join(part.capitalize() for part in signature["key"].split("_"))
        result.setdefault(pack, UpgradeBuildModel()).add(UpgradeDefinition(
            sid=f"BPRUEDLC{pack}{token}_Upgrade_BPRUE_Signature_{key_token}",
            general_setup_sid=weapon["general_setup_sid"],
            weapon_class=weapon_class,
            group="Signature",
            target_part=signature["target_part"],
            text_sid=f"sid_bprue_dlc_{pack.lower()}_{signature['key']}_name",
            hint_sid=f"sid_bprue_dlc_{pack.lower()}_{signature['key']}_description",
            image="",
            icon="Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Depreciation.T_PDA_Upgrades_Icon_Depreciation'",
            cost=int(signature["cost"]),
            effects=tuple(signature["effects"]),
            template_sid="BPRUE_ModuleTemplate",
            standalone=True,
        ))
        added += 1
    return added


def build_dlc_models(source_model: UpgradeBuildModel, configs: dict) -> dict[str, UpgradeBuildModel]:
    """Clone BPRUE base-family modules into one isolated model per DLC content pack.

    DLC modules and their signature modules stay separate from the base-game model,
    so their UpgradePrototypes and GeneralSetup registrations are rendered only
    below GameLite/DLCGameData/<pack>.
    """
    result: dict[str, UpgradeBuildModel] = {}
    source_by_setup = source_model.by_general_setup()
    weapons = load_dlc_config().get("weapons", {})

    for name, weapon in weapons.items():
        pack = weapon["content_pack"]
        class_name = weapon["class"]
        config_key = CLASS_CONFIG_KEYS.get(class_name)
        if not config_key or config_key not in configs:
            raise ValueError(f"{pack}/{name}: no loaded generator config for class {class_name}")

        class_config = configs[config_key]
        base_name = weapon["base_family"]
        base = class_config.get("families", {}).get(base_name)
        if not base:
            raise ValueError(f"{pack}/{name}: unknown {class_name} base_family {base_name}")

        base_setup = base["general_setup_sid"]
        base_prefix = base["prototype_prefix"]
        source_upgrades = source_by_setup.get(base_setup, [])
        if not source_upgrades:
            raise ValueError(f"{pack}/{name}: base family {base_name} ({base_setup}) has no BPRUE upgrades")

        target_setup = weapon["general_setup_sid"]
        prefix = weapon.get("prototype_prefix", _dlc_prefix(pack, name))
        sid_map = {upgrade.sid: _clone_sid(upgrade.sid, base_prefix, prefix) for upgrade in source_upgrades}
        target_model = result.setdefault(pack, UpgradeBuildModel())

        for source in source_upgrades:
            target_model.add(replace(
                source,
                sid=sid_map[source.sid],
                general_setup_sid=target_setup,
                additional_general_setup_sids=(),
                blocking_sids=tuple(sid_map.get(sid, sid) for sid in source.blocking_sids),
                required_upgrade_sids=tuple(sid_map.get(sid, sid) for sid in source.required_upgrade_sids),
                horizontal_position=None,
            ))

    _add_dlc_signatures(result, weapons)
    for model in result.values():
        model.validate()
    return result


def render_dlc_signature_effects(pack: str) -> str:
    """Render DLC signature effects into DLCGameData only.

    These use only effect types already exercised by Vanilla/BPRUE; the DLC layer
    introduces no new effect mechanics. Durability-per-shot effects inherit the
    same Vanilla DurabilityPerShotTemplate used by existing BPRUE effects.
    """
    if pack != "DLC1":
        return "// AUTO-GENERATED - no BPRUE signature effects for this DLC pack\n"

    specs = (
        ("ArmorPiercingPos15", "ArmorPiercing", "bprue_armor_piercing", "15%", "Positive"),
        ("ArmorPiercingPos20", "ArmorPiercing", "bprue_armor_piercing", "20%", "Positive"),
        ("ArmorPiercingPos25", "ArmorPiercing", "bprue_armor_piercing", "25%", "Positive"),
        ("RecoilPos15", "Recoil", "bprue_recoil", "-15%", "Positive"),
        ("RecoilPos20", "Recoil", "bprue_recoil", "-20%", "Positive"),
        ("RecoilPenalty10", "Recoil", "bprue_recoil", "10%", "Negative"),
        ("EffectiveRangePenalty10", "EffectiveFireDistance", "bprue_effective_range", "-10%", "Negative"),
        ("EffectiveRangePenalty15", "EffectiveFireDistance", "bprue_effective_range", "-15%", "Negative"),
        ("WeightDown10", "WeaponItemWeight", "bprue_weight", "-10%", "Positive"),
        ("WeightDown15", "WeaponItemWeight", "bprue_weight", "-15%", "Positive"),
        ("WeightPenalty5", "WeaponItemWeight", "bprue_weight", "5%", "Negative"),
        ("WeightPenalty10", "WeaponItemWeight", "bprue_weight", "10%", "Negative"),
        ("WeightPenalty15", "WeaponItemWeight", "bprue_weight", "15%", "Negative"),
        ("AimingTimePos15", "AimingTime", "bprue_aiming_speed", "-15%", "Positive"),
        ("AimingTimePos20", "AimingTime", "bprue_aiming_speed", "-20%", "Positive"),
        ("AimingTimePos25", "AimingTime", "bprue_aiming_speed", "-25%", "Positive"),
        ("DispersionPos20", "Dispersion", "bprue_accuracy", "-20%", "Positive"),
        ("DispersionPos25", "Dispersion", "bprue_accuracy", "-25%", "Positive"),
        ("DurabilityPos30", "Durability", "bprue_durability", "30%", "Positive"),
        ("FireIntervalNeg10", "FireInterval", "bprue_fire_rate", "-10%", "Positive"),
        ("FireIntervalNeg15", "FireInterval", "bprue_fire_rate", "-15%", "Positive"),
        ("DamagePenalty10", "WeaponDamage", "bprue_damage", "-10%", "Negative"),
    )
    durability_specs = (
        ("DurabilityPerShotPos15", "-15%", "Positive"),
        ("DurabilityPerShotPos25", "-25%", "Positive"),
        ("DurabilityPerShotPenalty10", "10%", "Negative"),
    )
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        f"// BPRUE signature effects for {pack}; intentionally scoped to DLCGameData.",
        "// Uses only established Vanilla/BPRUE effect mechanics.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for token, effect_type, localization, value, beneficial in specs:
        sid = f"BPRUE_{pack}_{token}Effect"
        lines += [
            f"{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}",
            f"   SID = {sid}",
            f"   Type = EEffectType::{effect_type}",
            f"   LocalizationSID = {localization}",
            f"   ValueMin = {value}",
            f"   ValueMax = {value}",
            "   bIsPermanent = true",
            f"   Positive = EBeneficial::{beneficial}",
            "   ShowUpgradeEffectValue = true",
            "   ShowUpgradeEffect = true",
            "struct.end",
            "",
        ]
    for token, value, beneficial in durability_specs:
        sid = f"BPRUE_{pack}_{token}Effect"
        lines += [
            f"{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=DurabilityPerShotTemplate}}",
            f"   SID = {sid}",
            "   LocalizationSID = bprue_weapon_wear",
            f"   ValueMin = {value}",
            f"   ValueMax = {value}",
            f"   Positive = EBeneficial::{beneficial}",
            "   ShowUpgradeEffectValue = true",
            "   ShowUpgradeEffect = true",
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"
