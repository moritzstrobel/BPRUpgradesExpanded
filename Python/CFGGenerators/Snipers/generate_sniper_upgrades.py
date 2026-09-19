from __future__ import annotations
import json
from pathlib import Path
from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from upgrade_renderers import render_general_setup_patch, render_upgrade_prototypes

SCRIPT_DIR=Path(__file__).resolve().parent
PYTHON_ROOT=SCRIPT_DIR.parents[1]
CONTENT_ROOT=PYTHON_ROOT.parent
CONFIG_PATH=SCRIPT_DIR/'sniper_upgrades.json'
UPGRADE_OUTPUT=CONTENT_ROOT/'GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_SniperUpgradePrototypes.cfg'
EFFECT_OUTPUT=CONTENT_ROOT/'GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_SniperEffectPrototypes.cfg'
WEAPON_OUTPUT=CONTENT_ROOT/'GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_SniperModules.cfg'
IMAGE="Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Sniper/M701/Barrel/Upgrade/T_M701_Upg_a_1.T_M701_Upg_a_1'"
ICON="Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Accuracy.T_PDA_Upgrades_Icon_Accuracy'"
CALIBER_ICON="Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_CaliberChange.T_PDA_Upgrades_Icon_CaliberChange'"
TEMPLATE_SID='BPRUE_SniperModuleTemplate'
BALLISTICS={'high_velocity':(4200,['ProjectileSpeedPos20Effect','DistanceDropOffLengthPos10Effect','BPRUE_Sniper_RecoilPenalty10Effect','BPRUE_DurabilityPerShotNeg10Effect']),'match_barrel':(4400,['DispersionPos25Effect','FireDistancePos15Effect','BPRUE_Sniper_AimingTimePenalty10Effect']),'heavy_barrel':(4300,['RecoilPos20Effect','ShotRecoveryPos20Effect','BPRUE_Sniper_WeightPenalty10Effect','BPRUE_Sniper_AimingTimePenalty10Effect'])}
ACTION={'rapid':(4500,['BPRUE_FireIntervalNeg20Effect','BPRUE_Sniper_RecoilPenalty15Effect','BPRUE_DurabilityPerShotNeg20Effect']),'precision':(4400,['BPRUE_Sniper_ShotRecoveryPos30Effect','DispersionPos10Effect','BPRUE_Sniper_FireIntervalPenalty10Effect']),'reinforced':(4300,['RecoilPos20Effect','DurabilityPos20Effect','BPRUE_Sniper_FireIntervalPenalty10Effect'])}
MARKSMAN={'snap_shooter':(4100,['BPRUE_Sniper_AimingTimePos20Effect','AimingMovementPos10Effect','BPRUE_Sniper_RecoilPenalty10Effect']),'field_marksman':(4200,['AimingMovementPos15Effect','IdleSwayXPos15Effect','IdleSwayYPos15Effect','ShotRecoveryPos10Effect']),'benchrest':(4400,['BPRUE_Sniper_IdleSwayXPos30Effect','BPRUE_Sniper_IdleSwayYPos30Effect','RecoilPos15Effect','BPRUE_Sniper_AimingTimePenalty15Effect','BPRUE_Sniper_WeightPenalty10Effect'])}
STOCK={'lightweight_stock':(3900,['AimingTimePos15Effect','AimingMovementPos10Effect','BPRUE_Sniper_RecoilPenalty10Effect']),'adjustable_stock':(4200,['IdleSwayXPos15Effect','IdleSwayYPos15Effect','AimingMovementPos10Effect','RecoilPos10Effect']),'precision_stock':(4500,['BPRUE_Sniper_IdleSwayXPos30Effect','BPRUE_Sniper_IdleSwayYPos30Effect','RecoilPos20Effect','ShotRecoveryPos20Effect','BPRUE_Sniper_AimingTimePenalty15Effect'])}
GROUPS=(("Ballistics",BALLISTICS,"Barrel","Top"),("Action",ACTION,"Barrel","Down"),("Marksman",MARKSMAN,"Body","Down"),("Stock",STOCK,"Stock","Top"))
CALIBER_CONVERSIONS={
    "A762Sniper": ("A762NATO","762NATO","sid_bprue_caliber_762_nato_name","sid_bprue_sniper_caliber_762sniper_to_762nato_description",4800,("BPRUE_ChangeCaliber762NATOEffect","BPRUE_ChangeAmmoTypesNo762Effect","BPRUE_ChangeAmmoTypes762NATOEffect","RecoilPos10Effect","BPRUE_Shared_DamagePenalty10Effect")),
    "A762NATO": ("A762Sniper","762Sniper","sid_bprue_caliber_762_eastern_name","sid_bprue_sniper_caliber_762nato_to_762sniper_description",5000,("ChangeCaliber762Effect","BPRUE_ChangeAmmoTypesNo762NATOEffect","ChangeAmmoTypes762Effect","BPRUE_DamagePos10Effect","BPRUE_ArmorPiercingPos15Effect","BPRUE_Sniper_RecoilPenalty15Effect","BPRUE_DurabilityPerShotNeg15Effect")),
}

def load_config(): return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
def module_sid(prefix,group,key): return f"{prefix}_Upgrade_BPRUE_Sniper_{group}_{key.title().replace('_','')}"

def build_upgrades(config):
    upgrades=[]
    for family in config['families'].values():
        scale=family.get('cost_scale',1.0); prefix=family['prototype_prefix']; setup=family['general_setup_sid']
        conversion=CALIBER_CONVERSIONS.get(family.get('base_caliber')) if family.get('bprue_caliber_conversion',True) else None
        if conversion:
            _,suffix,text,hint,cost,effects=conversion
            upgrades.append(UpgradeDefinition(sid=f"{prefix}_Upgrade_BPRUE_Sniper_Caliber_{suffix}",general_setup_sid=setup,weapon_class='Sniper',group='Caliber',target_part='Body',text_sid=text,hint_sid=hint,image=IMAGE,icon=CALIBER_ICON,cost=round(cost*scale),effects=tuple(effects),template_sid=TEMPLATE_SID))
        for group,definitions,target,vertical in GROUPS:
            group_sids=[module_sid(prefix,group,key) for key in definitions]
            for key,(cost,effects) in definitions.items():
                current=module_sid(prefix,group,key)
                upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=setup,weapon_class='Sniper',group=group,target_part=target,text_sid=f'sid_bprue_sniper_{key}_name',hint_sid=f'sid_bprue_sniper_{key}_description',image=IMAGE,icon=ICON,cost=round(cost*scale),effects=tuple(effects),blocking_sids=tuple(x for x in group_sids if x!=current),vertical_position=vertical,template_sid=TEMPLATE_SID))
    return upgrades

EFFECT_LOCALIZATION={'Recoil':'bprue_recoil','AimingTime':'bprue_aiming_speed','Weight':'bprue_weight','FireInterval':'bprue_fire_rate','Dispersion':'bprue_accuracy','ShotRecovery':'bprue_recoil_recovery','IdleSwayX':'bprue_aiming_stability','IdleSwayY':'bprue_aiming_stability','DurabilityPerShot':'bprue_weapon_wear'}

def render_effects():
    definitions=[('BPRUE_Sniper_RecoilPenalty10Effect','Recoil','10%','Negative'),('BPRUE_Sniper_RecoilPenalty15Effect','Recoil','15%','Negative'),('BPRUE_Sniper_RecoilPenalty20Effect','Recoil','20%','Negative'),('BPRUE_Sniper_AimingTimePenalty10Effect','AimingTime','10%','Negative'),('BPRUE_Sniper_AimingTimePenalty15Effect','AimingTime','15%','Negative'),('BPRUE_Sniper_AimingTimePos20Effect','AimingTime','-20%','Positive'),('BPRUE_Sniper_WeightPenalty10Effect','Weight','10%','Negative'),('BPRUE_Sniper_FireIntervalPenalty10Effect','FireInterval','10%','Negative'),('BPRUE_Sniper_FireIntervalPenalty25Effect','FireInterval','25%','Negative'),('BPRUE_Sniper_DispersionPenalty15Effect','Dispersion','15%','Negative'),('BPRUE_Sniper_FireIntervalNeg15Effect','FireInterval','-15%','Positive'),('BPRUE_Sniper_FireIntervalNeg25Effect','FireInterval','-25%','Positive'),('BPRUE_Sniper_FireIntervalNeg30Effect','FireInterval','-30%','Positive'),('BPRUE_Sniper_ShotRecoveryPos25Effect','ShotRecovery','-25%','Positive'),('BPRUE_Sniper_ShotRecoveryPos30Effect','ShotRecovery','-30%','Positive'),('BPRUE_Sniper_IdleSwayXPos30Effect','IdleSwayX','-30%','Positive'),('BPRUE_Sniper_IdleSwayYPos30Effect','IdleSwayY','-30%','Positive'),('BPRUE_DurabilityPerShotNeg15Effect','DurabilityPerShot','15%','Negative')]
    lines=['// AUTO-GENERATED - Source: sniper_upgrades.json','']
    for sid,effect_type,value,beneficial in definitions:
        lines += [f'{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}',f'   SID = {sid}',f'   Type = EEffectType::{effect_type}',f'   LocalizationSID = {EFFECT_LOCALIZATION[effect_type]}',f'   ValueMin = {value}',f'   ValueMax = {value}','   bIsPermanent = true',f'   Positive = EBeneficial::{beneficial}','   ShowUpgradeEffectValue = true','   ShowUpgradeEffect = true','struct.end','']
    return '\n'.join(lines)

def all_upgrade_sids(config): return [u.sid for u in build_upgrades(config)]
def main():
    config=load_config(); model=UpgradeBuildModel(); model.extend(build_upgrades(config)); model.validate()
    outputs={UPGRADE_OUTPUT:render_upgrade_prototypes(model,source='sniper_upgrades.json',template_sid=TEMPLATE_SID),EFFECT_OUTPUT:render_effects(),WEAPON_OUTPUT:render_general_setup_patch(model)}
    for path,content in outputs.items(): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf-8'); print(f'Generated {path}')
if __name__=='__main__': main()
