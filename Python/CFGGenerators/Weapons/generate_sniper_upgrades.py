from __future__ import annotations
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "sniper_upgrades.json"
UPGRADE_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_SniperUpgradePrototypes.cfg"
EFFECT_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_SniperEffectPrototypes.cfg"
WEAPON_OUTPUT = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_SniperModules.cfg"

BALLISTICS = {
    "high_velocity": (4200, ["ProjectileSpeedPos20Effect", "DistanceDropOffLengthPos10Effect", "BPRUE_Sniper_RecoilPenalty10Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "match_barrel": (4400, ["DispersionPos25Effect", "FireDistancePos15Effect", "BPRUE_Sniper_AimingTimePenalty10Effect"]),
    "heavy_barrel": (4300, ["RecoilPos20Effect", "ShotRecoveryPos20Effect", "BPRUE_Sniper_WeightPenalty10Effect", "BPRUE_Sniper_AimingTimePenalty10Effect"]),
}
ACTION = {
    "rapid": (4500, ["BPRUE_FireIntervalNeg20Effect", "BPRUE_Sniper_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
    "precision": (4400, ["BPRUE_Sniper_ShotRecoveryPos30Effect", "DispersionPos10Effect", "BPRUE_Sniper_FireIntervalPenalty10Effect"]),
    "reinforced": (4300, ["RecoilPos20Effect", "DurabilityPos20Effect", "BPRUE_Sniper_FireIntervalPenalty10Effect"]),
}
MARKSMAN = {
    "snap_shooter": (4100, ["BPRUE_Sniper_AimingTimePos20Effect", "AimingMovementPos10Effect", "BPRUE_Sniper_RecoilPenalty10Effect"]),
    "field_marksman": (4200, ["AimingMovementPos15Effect", "IdleSwayXPos15Effect", "IdleSwayYPos15Effect", "ShotRecoveryPos10Effect"]),
    "benchrest": (4400, ["BPRUE_Sniper_IdleSwayXPos30Effect", "BPRUE_Sniper_IdleSwayYPos30Effect", "RecoilPos15Effect", "BPRUE_Sniper_AimingTimePenalty15Effect", "BPRUE_Sniper_WeightPenalty10Effect"]),
}
SIGNATURES = {
    "rapid_marksman": (6000, ["BPRUE_Sniper_FireIntervalNeg25Effect", "ShotRecoveryPos20Effect", "AimingTimePos15Effect", "BPRUE_Sniper_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
    "recon_marksman": (6200, ["BPRUE_Sniper_AimingTimePos20Effect", "AimingMovementPos20Effect", "WeightPos15Effect", "BPRUE_Sniper_DispersionPenalty15Effect"]),
    "match_trigger": (6500, ["DispersionPos20Effect", "BPRUE_Sniper_ShotRecoveryPos30Effect", "BPRUE_FireIntervalNeg10Effect", "RecoilPos10Effect"]),
    "anti_materiel": (8500, ["DamagePos30Effect", "ArmorPiercingPos30Effect", "CoverPiercingPos30Effect", "ProjectileSpeedPos25Effect", "BPRUE_Sniper_FireIntervalPenalty25Effect", "BPRUE_DurabilityPerShotNeg20Effect", "BPRUE_Sniper_WeightPenalty10Effect"]),
    "battle_rifle": (6800, ["BPRUE_Sniper_FireIntervalNeg15Effect", "RecoilPos15Effect", "AimingMovementPos15Effect", "ShotRecoveryPos20Effect", "BPRUE_DurabilityPerShotNeg15Effect"]),
    "mad_minute": (6200, ["BPRUE_Sniper_FireIntervalNeg30Effect", "BPRUE_Sniper_ShotRecoveryPos25Effect", "AimingTimePos10Effect", "BPRUE_Sniper_RecoilPenalty20Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
}

IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Sniper/M701/Barrel/Upgrade/T_M701_Upg_a_1.T_M701_Upg_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Accuracy.T_PDA_Upgrades_Icon_Accuracy'"

def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

def module_sid(prefix: str, group: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Sniper_{group}_{key.title().replace('_', '')}"

def signature_sid(prefix: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Sniper_Signature_{key.title().replace('_', '')}"

def modules_for(family: dict) -> list[dict]:
    result = []
    scale = family.get("cost_scale", 1.0)
    for group, definitions in (("Ballistics", BALLISTICS), ("Action", ACTION), ("Marksman", MARKSMAN)):
        for key, (cost, effects) in definitions.items():
            result.append({
                "sid": module_sid(family["prototype_prefix"], group, key), "group": group, "key": key,
                "cost": round(cost * scale), "effects": effects,
                "block": [module_sid(family["prototype_prefix"], group, other) for other in definitions if other != key],
            })
    key = family["signature"]
    cost, effects = SIGNATURES[key]
    result.append({"sid": signature_sid(family["prototype_prefix"], key), "group": "Signature", "key": key, "cost": round(cost * scale), "effects": effects, "block": []})
    return result

def render_upgrades(config: dict) -> str:
    lines = ["// AUTO-GENERATED - Source: sniper_upgrades.json", "// Three mutually-exclusive specialization groups plus one standalone family signature.", "", "BPRUE_SniperModuleTemplate : struct.begin {refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}", "   SID = BPRUE_SniperModuleTemplate", "   IsModification = true", "struct.end", ""]
    for family in config["families"].values():
        for module in modules_for(family):
            target = "Barrel" if module["group"] in ("Ballistics", "Action", "Signature") else "Body"
            vertical = "Top" if module["group"] in ("Ballistics", "Signature") else "Down"
            lines += [f"{module['sid']} : struct.begin {{refkey=BPRUE_SniperModuleTemplate}}", f"   SID = {module['sid']}", f"   Text = sid_bprue_sniper_{module['key']}_name", f"   Hint = sid_bprue_sniper_{module['key']}_description", f"   Image = {IMAGE}", f"   Icon = {ICON}", f"   BaseCost = {module['cost']}", f"   VerticalPosition = EUpgradeVerticalPosition::{vertical}", f"   UpgradeTargetPart = EUpgradeTargetPartType::{target}", "   EffectPrototypeSIDs : struct.begin"]
            lines += [f"      [{i}] = {effect}" for i, effect in enumerate(module["effects"])] + ["   struct.end"]
            if module["block"]:
                lines += ["   BlockingUpgradePrototypeSIDs : struct.begin"] + [f"      [{i}] = {sid}" for i, sid in enumerate(module["block"])] + ["   struct.end"]
            lines += ["struct.end", ""]
    return "\n".join(lines)

def render_effects() -> str:
    definitions = [
        ("BPRUE_Sniper_RecoilPenalty10Effect", "Recoil", "10%", "Negative"),
        ("BPRUE_Sniper_RecoilPenalty15Effect", "Recoil", "15%", "Negative"),
        ("BPRUE_Sniper_RecoilPenalty20Effect", "Recoil", "20%", "Negative"),
        ("BPRUE_Sniper_AimingTimePenalty10Effect", "AimingTime", "10%", "Negative"),
        ("BPRUE_Sniper_AimingTimePenalty15Effect", "AimingTime", "15%", "Negative"),
        ("BPRUE_Sniper_AimingTimePos20Effect", "AimingTime", "-20%", "Positive"),
        ("BPRUE_Sniper_WeightPenalty10Effect", "Weight", "10%", "Negative"),
        ("BPRUE_Sniper_FireIntervalPenalty10Effect", "FireInterval", "10%", "Negative"),
        ("BPRUE_Sniper_FireIntervalPenalty25Effect", "FireInterval", "25%", "Negative"),
        ("BPRUE_Sniper_DispersionPenalty15Effect", "Dispersion", "15%", "Negative"),
        ("BPRUE_Sniper_FireIntervalNeg15Effect", "FireInterval", "-15%", "Positive"),
        ("BPRUE_Sniper_FireIntervalNeg25Effect", "FireInterval", "-25%", "Positive"),
        ("BPRUE_Sniper_FireIntervalNeg30Effect", "FireInterval", "-30%", "Positive"),
        ("BPRUE_Sniper_ShotRecoveryPos25Effect", "ShotRecovery", "-25%", "Positive"),
        ("BPRUE_Sniper_ShotRecoveryPos30Effect", "ShotRecovery", "-30%", "Positive"),
        ("BPRUE_Sniper_IdleSwayXPos30Effect", "IdleSwayX", "-30%", "Positive"),
        ("BPRUE_Sniper_IdleSwayYPos30Effect", "IdleSwayY", "-30%", "Positive"),
        ("BPRUE_DurabilityPerShotNeg15Effect", "DurabilityPerShot", "15%", "Negative"),
    ]
    lines = ["// AUTO-GENERATED - Source: sniper_upgrades.json", ""]
    for sid, effect_type, value, beneficial in definitions:
        lines += [
            f"{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}",
            f"   SID = {sid}",
            f"   Type = EEffectType::{effect_type}",
            f"   ValueMin = {value}",
            f"   ValueMax = {value}",
            "   bIsPermanent = true",
            f"   Positive = EBeneficial::{beneficial}",
            "struct.end",
            "",
        ]
    return "\n".join(lines)

def render_weapons(config: dict) -> str:
    lines = ["// AUTO-GENERATED - Source: sniper_upgrades.json", "// Vintar, GP3A and unique variants are intentionally excluded from this pass.", ""]
    for family in config["families"].values():
        lines += [f"{family['general_setup_sid']} : struct.begin {{bpatch}}", "   UpgradePrototypeSIDs : struct.begin {bpatch}"]
        lines += [f"      [*] = {module['sid']}" for module in modules_for(family)]
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)

def all_upgrade_sids(config: dict) -> list[str]:
    return [module["sid"] for family in config["families"].values() for module in modules_for(family)]

def main() -> None:
    config = load_config()
    for path, content in {UPGRADE_OUTPUT: render_upgrades(config), EFFECT_OUTPUT: render_effects(), WEAPON_OUTPUT: render_weapons(config)}.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")

if __name__ == "__main__":
    main()
