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


def signature_sid(prefix: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Pistol_Signature_{key.title().replace('_', '')}"


def signature_for(family: dict) -> dict:
    key = family["signature"]
    cost, effects = SIGNATURES[key]
    return {
        "sid": signature_sid(family["prototype_prefix"], key),
        "key": key,
        "cost": round(cost * family.get("cost_scale", 1.0)),
        "effects": effects,
    }


def render_upgrades(config: dict) -> str:
    lines = [
        "// AUTO-GENERATED - Source: pistol_upgrades.json",
        "// Phase 1: standalone signature modules only. Shared pistol groups follow separately.",
        "",
        "BPRUE_PistolSignatureTemplate : struct.begin {refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}",
        "   SID = BPRUE_PistolSignatureTemplate",
        "   IsModification = true",
        "struct.end",
        "",
    ]
    for family in config["families"].values():
        module = signature_for(family)
        lines += [
            f"{module['sid']} : struct.begin {{refkey=BPRUE_PistolSignatureTemplate}}",
            f"   SID = {module['sid']}",
            f"   Text = sid_bprue_pistol_{module['key']}_name",
            f"   Hint = sid_bprue_pistol_{module['key']}_description",
            f"   Image = {IMAGE}",
            f"   Icon = {ICON}",
            f"   BaseCost = {module['cost']}",
            "   VerticalPosition = EUpgradeVerticalPosition::Top",
            "   UpgradeTargetPart = EUpgradeTargetPartType::Barrel",
            "   EffectPrototypeSIDs : struct.begin",
        ]
        lines += [f"      [{i}] = {effect}" for i, effect in enumerate(module["effects"])]
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def render_effects() -> str:
    return """// AUTO-GENERATED - Source: pistol_upgrades.json
// Pistol-specific effects required by the signature modules.

BPRUE_Pistol_RecoilPenalty15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Pistol_RecoilPenalty15Effect
   Type = EEffectType::Recoil
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Negative
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
    lines = [
        "// AUTO-GENERATED - Source: pistol_upgrades.json",
        "// Registers one standalone signature module on each normal pistol family.",
        "",
    ]
    for family in config["families"].values():
        module = signature_for(family)
        lines += [
            f"{family['general_setup_sid']} : struct.begin {{bpatch}}",
            "   UpgradePrototypeSIDs : struct.begin {bpatch}",
            f"      [*] = {module['sid']}",
            "   struct.end",
            "struct.end",
            "",
        ]
    return "\n".join(lines)


def all_upgrade_sids(config: dict) -> list[str]:
    return [signature_for(family)["sid"] for family in config["families"].values()]


def main() -> None:
    config = load_config()
    for path, content in {
        UPGRADE_OUTPUT: render_upgrades(config),
        EFFECT_OUTPUT: render_effects(),
        WEAPON_OUTPUT: render_weapons(config),
    }.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")


if __name__ == "__main__":
    main()
