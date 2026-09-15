from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from upgrade_renderers import render_general_setup_patch, render_upgrade_prototypes

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "pistol_upgrades.json"
UPGRADE_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_PistolUpgradePrototypes.cfg"
EFFECT_OUTPUT = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_PistolEffectPrototypes.cfg"
WEAPON_OUTPUT = CONTENT_ROOT / "GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_PistolModules.cfg"

TEMPLATE_SID = "BPRUE_PistolModuleTemplate"
ACTION = {
    "high_speed": (2200, ["BPRUE_FireIntervalNeg20Effect", "BPRUE_Pistol_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
    "balanced": (2100, ["BPRUE_FireIntervalNeg10Effect", "RecoilPos10Effect", "ShotRecoveryPos20Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "controlled": (2200, ["BPRUE_Pistol_FireIntervalPos10Effect", "RecoilPos15Effect", "ShotRecoveryPos20Effect"]),
}
HANDLING = {
    "quick_draw": (2000, ["WeightPos15Effect", "AimingTimePos15Effect", "BPRUE_Pistol_RecoilPenalty10Effect"]),
    "tactical": (2100, ["AimingTimePos10Effect", "AimingMovementPos10Effect", "ShotRecoveryPos10Effect"]),
    "stabilized": (2200, ["RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]),
}
SIGNATURES = {
    "quick_response": (2600, ["AimingTimePos20Effect", "BPRUE_ReloadingTimeNeg20Effect", "WeightPos15Effect", "BPRUE_Pistol_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "match_barrel": (3200, ["DispersionPos30Effect", "DistanceDropOffLengthPos20Effect", "ProjectileSpeedPos20Effect", "AimingTimeNeg10Effect"]),
    "automatic_sear": (3800, ["ChangeFireTypeEffectBurstAuto", "BPRUE_Pistol_RecoilPenalty15Effect", "BPRUE_DurabilityPerShotNeg20Effect"]),
    "hunting_cylinder": (4500, ["ArmorPiercingPos20Effect", "ProjectileSpeedPos20Effect", "BPRUE_Pistol_FireIntervalPos10Effect"]),
    "selectable_fire_control": (3200, ["ChangeFireTypeEffectSemiAuto", "RecoilPos10Effect"]),
}
IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Handgun/APB/Barrel/Upgrade/T_APBU_a_1.T_APBU_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def module_sid(prefix: str, group: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Pistol_{group}_{key.title().replace('_', '')}"


def signature_sid(prefix: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_Pistol_Signature_{key.title().replace('_', '')}"


def build_upgrades(config: dict) -> list[UpgradeDefinition]:
    result: list[UpgradeDefinition] = []
    for family in config["families"].values():
        prefix = family["prototype_prefix"]
        setup = family["general_setup_sid"]
        scale = family.get("cost_scale", 1.0)
        for group, definitions, target, vertical in (
            ("Action", ACTION, "Barrel", "Top"),
            ("Handling", HANDLING, "Body", "Down"),
        ):
            group_sids = [module_sid(prefix, group, key) for key in definitions]
            for key, (cost, effects) in definitions.items():
                current = module_sid(prefix, group, key)
                result.append(UpgradeDefinition(
                    sid=current, general_setup_sids=(setup,), weapon_class="Pistol", group=group,
                    target_part=target, text_sid=f"sid_bprue_pistol_{key}_name",
                    hint_sid=f"sid_bprue_pistol_{key}_description", image=IMAGE, icon=ICON,
                    cost=round(cost * scale), effects=tuple(effects),
                    blocking_sids=tuple(sid for sid in group_sids if sid != current),
                    vertical_position=vertical, template_sid=TEMPLATE_SID,
                ))
        key = family["signature"]
        cost, effects = SIGNATURES[key]
        result.append(UpgradeDefinition(
            sid=signature_sid(prefix, key), general_setup_sids=(setup,), weapon_class="Pistol",
            group="Signature", target_part="Barrel", text_sid=f"sid_bprue_pistol_{key}_name",
            hint_sid=f"sid_bprue_pistol_{key}_description", image=IMAGE, icon=ICON,
            cost=round(cost * scale), effects=tuple(effects), vertical_position="Top",
            template_sid=TEMPLATE_SID,
        ))
    return result


def render_effects() -> str:
    return """// AUTO-GENERATED - Source: pistol_upgrades.json
// Pistol-specific effects required by the shared groups and signature modules.

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


def all_upgrade_sids(config: dict) -> list[str]:
    return [upgrade.sid for upgrade in build_upgrades(config)]


def main() -> None:
    config = load_config()
    model = UpgradeBuildModel()
    model.extend(build_upgrades(config))
    model.validate()
    outputs = {
        UPGRADE_OUTPUT: render_upgrade_prototypes(
            model, source="pistol_upgrades.json", template_sid=TEMPLATE_SID,
            header_comments=("Two mutually-exclusive three-way groups plus one standalone family signature.",),
        ),
        EFFECT_OUTPUT: render_effects(),
        WEAPON_OUTPUT: render_general_setup_patch(
            model,
            header_comments=("Registers two three-way specialization groups and one signature per normal pistol family.",),
        ),
    }
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Generated {path}")
    print(f"Generated pistol specialization CFGs from {model.summary()}")


if __name__ == "__main__":
    main()
