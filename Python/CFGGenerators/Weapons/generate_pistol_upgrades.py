from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "pistol_upgrades.json"
UPGRADE_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_PistolUpgradePrototypes.cfg"
EFFECT_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_PistolEffectPrototypes.cfg"
WEAPON_OUTPUT = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_PistolModules.cfg"

ACTION = {
    "high_speed": (2200, ["BPRUE_FireIntervalNeg20Effect", "BPRUE_Pistol_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
    "balanced": (2100, ["BPRUE_FireIntervalNeg10Effect", "RecoilDown10Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "controlled": (2200, ["BPRUE_Pistol_FireIntervalPos10Effect", "RecoilDown15Effect", "ShotRecoveryPos20Effect"]),
}
HANDLING = {
    "quick_draw": (2000, ["WeightDown15Effect", "AimingTimePos15Effect", "BPRUE_Pistol_RecoilPenalty10Effect"]),
    "tactical": (2100, ["AimingTimePos10Effect", "AimingMovementPos10Effect", "ShotRecoveryPos10Effect"]),
    "stabilized": (2200, ["RecoilDown15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]),
}
SIGNATURES = {
    "quick_response": (2600, ["AimingTimePos20Effect", "BPRUE_ReloadingTimeNeg20Effect", "WeightDown15Effect", "BPRUE_Pistol_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "match_barrel": (3200, ["DispersionPos30Effect", "DistanceDropOffLengthPos20Effect", "ProjectileSpeedPos20Effect", "AimingTimeNeg10Effect"]),
    "automatic_sear": (3800, ["ChangeFireTypeEffectBurstAuto", "BPRUE_Pistol_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
    "hunting_cylinder": (4500, ["ArmorPiercingPos20Effect", "ProjectileSpeedPos20Effect", "BPRUE_Pistol_FireIntervalPos10Effect"]),
    "selectable_fire_control": (3200, ["ChangeFireTypeEffectSemiAuto", "RecoilDown10Effect"]),
}

IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Handgun/APB/Barrel/Upgrade/T_APBU_a_1.T_APBU_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def module_sid(prefix: str, group: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Pistol_{group}_{key.title().replace('_', '')}"


def signature_sid(prefix: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Pistol_Signature_{key.title().replace('_', '')}"


def modules_for(family: dict) -> list[dict]:
    result = []
    scale = family.get("cost_scale", 1.0)
    for group, definitions in (("Action", ACTION), ("Handling", HANDLING)):
        for key, (cost, effects) in definitions.items():
            result.append({
                "sid": module_sid(family["prototype_prefix"], group, key),
                "group": group,
                "key": key,
                "cost": round(cost * scale),
                "effects": effects,
                "block": [module_sid(family["prototype_prefix"], group, other) for other in definitions if other != key],
            })
    key = family["signature"]
    cost, effects = SIGNATURES[key]
    result.append({"sid": signature_sid(family["prototype_prefix"], key), "group": "Signature", "key": key, "cost": round(cost * scale), "effects": effects, "block": []})
    return result


def render_upgrades(config: dict) -> str:
    lines = ["// AUTO-GENERATED - Source: pistol_upgrades.json", "", "BPRUE_PistolModuleTemplate : struct.begin {refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}", "   SID = BPRUE_PistolModuleTemplate", "   IsModification = true", "struct.end", ""]
    for family in config["families"].values():
        for module in modules_for(family):
            target = "Barrel" if module["group"] in ("Action", "Signature") else "Body"
            lines += [f"{module['sid']} : struct.begin {{refkey=BPRUE_PistolModuleTemplate}}", f"   SID = {module['sid']}", f"   Text = sid_bprue_pistol_{module['key']}_name", f"   Hint = sid_bprue_pistol_{module['key']}_description", f"   Image = {IMAGE}", f"   Icon = {ICON}", f"   BaseCost = {module['cost']}", "   VerticalPosition = EUpgradeVerticalPosition::Top", f"   UpgradeTargetPart = EUpgradeTargetPartType::{target}", "   EffectPrototypeSIDs : struct.begin"]
            lines += [f"      [{i}] = {effect}" for i, effect in enumerate(module["effects"])]
            lines += ["   struct.end"]
            if module["block"]:
                lines += ["   BlockingUpgradePrototypeSIDs : struct.begin"] + [f"      [{i}] = {sid}" for i, sid in enumerate(module["block"])] + ["   struct.end"]
            lines += ["struct.end", ""]
    return "\n".join(lines)


def render_effects() -> str:
    return """// AUTO-GENERATED - Source: pistol_upgrades.json

BPRUE_Pistol_RecoilPenalty10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Pistol_RecoilPenalty10Effect
   Type = EEffectType::Recoil
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
struct.end
BPRUE_Pistol_RecoilPenalty15Effect : struct.begin {refkey=BPRUE_Pistol_RecoilPenalty10Effect}
   SID = BPRUE_Pistol_RecoilPenalty15Effect
   ValueMin = 15%
   ValueMax = 15%
struct.end
BPRUE_Pistol_FireIntervalPos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Pistol_FireIntervalPos10Effect
   Type = EEffectType::FireInterval
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
struct.end
"""


def render_weapons(config: dict) -> str:
    lines = ["// AUTO-GENERATED - Source: pistol_upgrades.json", ""]
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
