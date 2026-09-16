from __future__ import annotations

import json
from pathlib import Path

from upgrade_build_model import UpgradeDefinition

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "machine_gun_upgrades.json"

IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/MG/PKP/Barrel/Upgrade/T_PKP_Upg_a_1.T_PKP_Upg_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Accuracy.T_PDA_Upgrades_Icon_Accuracy'"
TEMPLATE_SID = "BPRUE_MachineGunModuleTemplate"

SUSTAINED_FIRE = {
    "high_output": (4800, ["BPRUE_FireIntervalNeg10Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "controlled_fire": (4700, ["RecoilPos15Effect", "DispersionPos10Effect", "BPRUE_MG_FireIntervalPenalty10Effect"]),
}
HEAVY_BARREL = {
    "heat_resistant": (5000, ["DurabilityPos20Effect", "BPRUE_MG_WeightPenalty10Effect"]),
    "stabilized_barrel": (5100, ["RecoilPos20Effect", "ShotRecoveryPos20Effect", "BPRUE_MG_WeightPenalty10Effect"]),
}
FEED_SYSTEM = {
    "fast_feed": (4600, ["BPRUE_ReloadingTimeNeg20Effect", "BPRUE_DurabilityPerShotNeg10Effect"]),
    "reinforced_feed": (4700, ["DurabilityPos20Effect", "BPRUE_MG_ReloadPenalty10Effect"]),
}
SUPPORT = {
    "mobile_support": (4500, ["WeightPos15Effect", "AimingTimePos15Effect", "BPRUE_MG_RecoilPenalty10Effect"]),
    "stable_support": (4900, ["RecoilPos20Effect", "DispersionPos15Effect", "BPRUE_MG_WeightPenalty10Effect"]),
}

GROUPS = (
    ("SustainedFire", SUSTAINED_FIRE, "Body"),
    ("HeavyBarrel", HEAVY_BARREL, "Barrel"),
    ("FeedSystem", FEED_SYSTEM, "Body"),
    ("Support", SUPPORT, "Stock"),
)


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def module_sid(prefix: str, group: str, key: str) -> str:
    return f"{prefix}_Upgrade_BPRUE_MG_{group}_{key.title().replace('_', '')}"


def build_upgrades(config):
    upgrades = []
    for family in config["families"].values():
        scale = family.get("cost_scale", 1.0)
        prefix = family["prototype_prefix"]
        setup = family["general_setup_sid"]
        for group, definitions, target in GROUPS:
            group_sids = [module_sid(prefix, group, key) for key in definitions]
            for key, (cost, effects) in definitions.items():
                current = module_sid(prefix, group, key)
                upgrades.append(UpgradeDefinition(
                    sid=current,
                    general_setup_sid=setup,
                    weapon_class="MG",
                    group=group,
                    target_part=target,
                    text_sid=f"sid_bprue_mg_{key}_name",
                    hint_sid=f"sid_bprue_mg_{key}_description",
                    image=IMAGE,
                    icon=ICON,
                    cost=round(cost * scale),
                    effects=tuple(effects),
                    blocking_sids=tuple(x for x in group_sids if x != current),
                    vertical_position="Top",
                    template_sid=TEMPLATE_SID,
                ))
    return upgrades


EFFECT_LOCALIZATION = {
    "Recoil": "bprue_recoil",
    "Weight": "bprue_weight",
    "FireInterval": "bprue_fire_rate",
    "ReloadingTime": "bprue_reload_speed",
}


def render_effects():
    definitions = [
        ("BPRUE_MG_FireIntervalPenalty10Effect", "FireInterval", "10%", "Negative"),
        ("BPRUE_MG_WeightPenalty10Effect", "Weight", "10%", "Negative"),
        ("BPRUE_MG_ReloadPenalty10Effect", "ReloadingTime", "10%", "Negative"),
        ("BPRUE_MG_RecoilPenalty10Effect", "Recoil", "10%", "Negative"),
    ]
    lines = ["// AUTO-GENERATED - Source: machine_gun_upgrades.json", ""]
    for sid, effect_type, value, beneficial in definitions:
        lines += [
            f"{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}",
            f"   SID = {sid}",
            f"   Type = EEffectType::{effect_type}",
            f"   LocalizationSID = {EFFECT_LOCALIZATION[effect_type]}",
            f"   ValueMin = {value}",
            f"   ValueMax = {value}",
            "   bIsPermanent = true",
            f"   Positive = EBeneficial::{beneficial}",
            "   ShowUpgradeEffectValue = true",
            "   ShowUpgradeEffect = true",
            "struct.end",
            "",
        ]
    return "\n".join(lines)
