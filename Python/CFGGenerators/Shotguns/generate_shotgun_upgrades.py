from __future__ import annotations
import json
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from upgrade_renderers import render_general_setup_patch, render_upgrade_prototypes

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / 'shotgun_upgrades.json'
UPGRADE_OUTPUT = CONTENT_ROOT / 'GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_ShotgunUpgradePrototypes.cfg'
EFFECT_OUTPUT = CONTENT_ROOT / 'GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_ShotgunEffectPrototypes.cfg'
WEAPON_OUTPUT = CONTENT_ROOT / 'GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_ShotgunModules.cfg'
IMAGE = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Shotgun/SPSA/Barrel/Upgrade/T_SPAS_Upg_a_1.T_SPAS_Upg_a_1'"
ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'"
TEMPLATE_SID = 'BPRUE_ShotgunModuleTemplate'
PATTERN = {
    'breacher': ('Breaching Barrel', 'Built for room clearing: 16 buckshot pellets and a much wider pattern, but 15% shorter effective falloff distance.', 2800, ['BPRUE_SG_FractionCount16Effect', 'DispersionNeg40Effect', 'BPRUE_SG_DistanceDropOffNeg15Effect']),
    'field_choke': ('Field Choke', 'A versatile choke keeping the standard 12-pellet load while tightening spread by 15% and extending falloff distance by 10%.', 3000, ['BPRUE_SG_FractionCount12Effect', 'DispersionPos15Effect', 'DistanceDropOffLengthPos10Effect']),
    'full_choke': ('Full Choke', 'A long-range setup using 10 pellets in a 30% tighter pattern with 20% longer falloff distance.', 3200, ['BPRUE_SG_FractionCount10Effect', 'DispersionPos30Effect', 'DistanceDropOffLengthPos20Effect']),
}
ACTION = {
    'high_speed': ('High-Speed Action', 'Cuts the firing cycle by 20%, but increases recoil by 15% and weapon wear by 20%.', 3200, ['BPRUE_FireIntervalNeg20Effect', 'BPRUE_SG_RecoilPenalty15Effect', 'BPRUE_DurabilityPerShotNeg20Effect']),
    'tuned': ('Tuned Action', 'Cuts the firing cycle by 10% and reduces recoil by 10%, at the cost of 10% increased weapon wear.', 3000, ['BPRUE_FireIntervalNeg10Effect', 'RecoilDown10Effect', 'BPRUE_DurabilityPerShotNeg10Effect']),
    'reinforced': ('Reinforced Action', 'Slows the firing cycle by 10% in exchange for 15% less recoil and 20% faster recoil recovery.', 3000, ['BPRUE_SG_FireIntervalPos10Effect', 'RecoilDown15Effect', 'ShotRecoveryPos20Effect']),
}
HANDLING = {
    'lightweight': ('Lightweight Furniture', 'Cuts weapon weight by 15% and speeds aiming by 15%, but increases recoil by 15%.', 2800, ['WeightDown15Effect', 'AimingTimePos15Effect', 'BPRUE_SG_RecoilPenalty15Effect']),
    'combat': ('Combat Furniture', 'Improves close-range handling with 10% faster aiming, 10% faster movement while aiming and 10% faster recoil recovery, but increases weapon wear by 10%.', 3000, ['AimingTimePos10Effect', 'AimingMovementPos10Effect', 'ShotRecoveryPos10Effect', 'BPRUE_DurabilityPerShotNeg10Effect']),
    'stabilized': ('Stabilized Furniture', 'Reduces recoil by 15% and improves recoil recovery by 20%, but makes the weapon 5% heavier and aiming 10% slower.', 3200, ['RecoilDown15Effect', 'ShotRecoveryPos20Effect', 'BPRUE_SG_WeightPos5Effect', 'AimingTimeNeg10Effect']),
}
GROUPS = [('Pattern', PATTERN, 'Barrel'), ('Action', ACTION, 'Body'), ('Handling', HANDLING, 'Body')]

def cfg() -> dict: return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
def sid(prefix: str, group: str, key: str) -> str: return f'{prefix}_Upgrade_BPRUE_SG_{group}_{key.title().replace("_", "")}'

def expanded_families(config: dict):
    """Yield normal families plus unique variants expanded from a base family."""
    for name, family in config['families'].items():
        yield name, family, False
    for name, unique in config.get('uniques', {}).items():
        base_name = unique['base_family']
        if base_name not in config['families']:
            raise ValueError(f'Unique shotgun {name} references unknown base_family {base_name}')
        family = dict(config['families'][base_name])
        family.update(unique)
        yield name, family, True

def build_upgrades(config: dict) -> list[UpgradeDefinition]:
    upgrades=[]
    for _, fam, _ in expanded_families(config):
        scale=fam.get('cost_scale',1)
        for group,definitions,target_part in GROUPS:
            group_sids=[sid(fam['prototype_prefix'],group,key) for key in definitions]
            for key,(_,_,cost,effects) in definitions.items():
                current=sid(fam['prototype_prefix'],group,key)
                upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=fam['general_setup_sid'],weapon_class='SG',group=group,target_part=target_part,
                    text_sid=f'sid_bprue_sg_{group.lower()}_{key}_name',hint_sid=f'sid_bprue_sg_{group.lower()}_{key}_description',image=IMAGE,icon=ICON,cost=round(cost*scale),
                    effects=tuple(effects),blocking_sids=tuple(other for other in group_sids if other!=current),vertical_position='Top',template_sid=TEMPLATE_SID))
    return upgrades

def render_effects() -> str:
    return '''// AUTO-GENERATED - Source: shotgun_upgrades.json

BPRUE_SG_FractionCount16Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_FractionCount16Effect
   Type = EEffectType::FractionCount
   LocalizationSID = bprue_pellet_count
   ValueMin = 16
   ValueMax = 16
   AmmoType = EAmmoType::Default
   bIsPermanent = true
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
BPRUE_SG_FractionCount12Effect : struct.begin {refkey=BPRUE_SG_FractionCount16Effect}
   SID = BPRUE_SG_FractionCount12Effect
   ValueMin = 12
   ValueMax = 12
struct.end
BPRUE_SG_FractionCount10Effect : struct.begin {refkey=BPRUE_SG_FractionCount16Effect}
   SID = BPRUE_SG_FractionCount10Effect
   ValueMin = 10
   ValueMax = 10
struct.end
BPRUE_SG_DistanceDropOffNeg15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=DistanceDropOffLengthTemplate}
   SID = BPRUE_SG_DistanceDropOffNeg15Effect
   LocalizationSID = bprue_effective_range
   ValueMin = -15%
   ValueMax = -15%
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
BPRUE_SG_RecoilPenalty15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_RecoilPenalty15Effect
   Type = EEffectType::Recoil
   LocalizationSID = bprue_recoil
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
BPRUE_SG_FireIntervalPos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_FireIntervalPos10Effect
   Type = EEffectType::FireInterval
   LocalizationSID = bprue_fire_rate
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
BPRUE_SG_WeightPos5Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_WeightPos5Effect
   Type = EEffectType::WeaponItemWeight
   LocalizationSID = bprue_weight
   ValueMin = 5%
   ValueMax = 5%
   bIsPermanent = true
   Positive = EBeneficial::Negative
   ShowUpgradeEffectValue = true
   ShowUpgradeEffect = true
struct.end
'''

def main() -> None:
    config=cfg(); model=UpgradeBuildModel(); model.extend(build_upgrades(config)); model.validate()
    outputs={UPGRADE_OUTPUT:render_upgrade_prototypes(model,source='shotgun_upgrades.json',template_sid=TEMPLATE_SID,header_comments=('Normal families and configured unique variants receive the same base-family specialization groups with distinct prototype SIDs.',)),EFFECT_OUTPUT:render_effects(),WEAPON_OUTPUT:render_general_setup_patch(model,header_comments=('Registers BPRUE specialization groups for normal shotgun families and configured unique variants.',))}
    for path,content in outputs.items(): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf8')
    print(f'Generated shotgun specialization CFGs from {model.summary()}')

if __name__=='__main__': main()
