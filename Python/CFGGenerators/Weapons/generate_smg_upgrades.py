from __future__ import annotations

import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "smg_upgrades.json"
UPGRADE_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "ModGameData" / "BPRUpgradesExpanded" / "UpgradePrototypes" / "BPRUE_SMGUpgradePrototypes.cfg"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "ModGameData" / "BPRUpgradesExpanded" / "EffectPrototypes" / "BPRUE_SMGEffectPrototypes.cfg"
WEAPON_OUTPUT_PATH = CONTENT_ROOT / "GameLite" / "GameData" / "WeaponData" / "WeaponGeneralSetupPrototypes" / "WeaponGeneralSetupPrototypes_patch_BPRUE_SMGModules.cfg"

MODULES = {
    "quick_draw": ("Readiness_QuickDraw", "sid_bprue_smg_quick_draw_name", "sid_bprue_smg_quick_draw_description", 2200, "Top", "Body", ["AimingTimePos15Effect", "AimingMovementPos10Effect", "BPRUE_SMG_ReloadingTimePos10Effect"]),
    "stabilized": ("Readiness_Stabilized", "sid_bprue_smg_stabilized_name", "sid_bprue_smg_stabilized_description", 2400, "Top", "Body", ["RecoilPos15Effect", "ShotRecoveryPos20Effect", "AimingTimeNeg10Effect"]),
    "competition_reload": ("Reload_Competition", "sid_bprue_smg_competition_reload_name", "sid_bprue_smg_competition_reload_description", 2400, "Down", "Body", ["BPRUE_ReloadingTimeNeg20Effect", "AimingTimeNeg10Effect"]),
    "tactical_reload": ("Reload_Tactical", "sid_bprue_smg_tactical_reload_name", "sid_bprue_smg_tactical_reload_description", 2300, "Down", "Body", ["BPRUE_ReloadingTimeNeg10Effect", "AimingTimePos15Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "high_speed_action": ("Action_HighSpeed", "sid_bprue_smg_high_speed_action_name", "sid_bprue_smg_high_speed_action_description", 3000, "Top", "Barrel", ["BPRUE_FireIntervalNeg20Effect", "RecoilNeg15Effect", "BPRUE_DurabilityPerShotNeg20Effect", "BPRUE_SMG_ReloadingTimePos10Effect"]),
    "controlled_action": ("Action_Controlled", "sid_bprue_smg_controlled_action_name", "sid_bprue_smg_controlled_action_description", 2800, "Top", "Barrel", ["BPRUE_FireIntervalPos5Effect", "RecoilPos15Effect", "ShotRecoveryPos20Effect", "BPRUE_ReloadingTimeNeg10Effect"]),
}
IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Assault/AK74/Barrel/Upgrade/T_AK47_Upg_a_1.T_AK47_Upg_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"

def load_config(): return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
def sid(key): return f"BPRUE_SMG_Upgrade_{MODULES[key][0]}"

def array(name, values):
    return [f"   {name} : struct.begin", *[f"      [{i}] = {v}" for i, v in enumerate(values)], "   struct.end"]

def render_upgrades(config):
    lines = ["// AUTO-GENERATED - Source: smg_upgrades.json", "", "BPRUE_SMGModuleTemplate : struct.begin {refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}", "   SID = BPRUE_SMGModuleTemplate", "   IsModification = true", "struct.end", ""]
    for group, keys in config["module_groups"].items():
        group_sids = [sid(k) for k in keys]
        for key in keys:
            suffix, text, hint, cost, vertical, target, effects = MODULES[key]; current = sid(key)
            lines += [f"{current} : struct.begin {{refkey=BPRUE_SMGModuleTemplate}}", f"   SID = {current}", f"   Text = {text}", f"   Hint = {hint}", f"   Image = {IMAGE}", f"   Icon = {ICON}", f"   BaseCost = {cost}", f"   VerticalPosition = EUpgradeVerticalPosition::{vertical}", f"   UpgradeTargetPart = EUpgradeTargetPartType::{target}"]
            lines += array("EffectPrototypeSIDs", effects) + array("BlockingUpgradePrototypeSIDs", [x for x in group_sids if x != current]) + ["struct.end", ""]
    return "\n".join(lines)

def render_effects():
    return """// AUTO-GENERATED - Source: smg_upgrades.json

BPRUE_SMG_ReloadingTimePos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SMG_ReloadingTimePos10Effect
   Text = Increase Reloading Time
   Type = EEffectType::ReloadingTime
   LocalizationSID = bprue_reload_speed
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
"""

def render_weapons(config):
    module_sids = [sid(key) for keys in config["module_groups"].values() for key in keys]
    lines = ["// AUTO-GENERATED - Source: smg_upgrades.json", "", "// Shared specialization modules; each pair is mutually exclusive.", ""]
    for name, family in config["families"].items():
        lines += [f"{family['weapon_sid']} : struct.begin {{bpatch}}", "   UpgradePrototypeSIDs : struct.begin {bpatch}", *[f"      [*] = {x}" for x in module_sids], "   struct.end", "struct.end", ""]
    return "\n".join(lines)

def main():
    config = load_config()
    for path, content in {UPGRADE_OUTPUT_PATH: render_upgrades(config), EFFECT_OUTPUT_PATH: render_effects(), WEAPON_OUTPUT_PATH: render_weapons(config)}.items():
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8"); print(f"Generated {path}")

if __name__ == "__main__": main()
