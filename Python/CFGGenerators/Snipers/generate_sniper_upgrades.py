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
AMMO_ICON_ROOT="/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Ammo"

def _ammo_icon(name):
    asset=f"T_Module_Ammo_{name}"
    return f"Texture2D'{AMMO_ICON_ROOT}/{asset}.{asset}'"

CALIBER_CONVERSIONS={
    "A762Sniper": {
        "target":"A762NATO","suffix":"762NATO","cost":4800,
        "change_effect":"BPRUE_ChangeCaliber762NATOEffect","remove_effect":"BPRUE_ChangeAmmoTypesNo762Effect",
        "variants":{
            "Default":("","sid_bprue_caliber_762_nato_name","sid_bprue_sniper_caliber_762sniper_to_762nato_description","BPRUE_ChangeAmmoTypes762NATOEffect",("RecoilPos10Effect","BPRUE_Shared_DamagePenalty10Effect"),_ammo_icon("762x51")),
            "AP":("_AP","sid_bprue_sniper_caliber_762nato_ap_name","sid_bprue_sniper_caliber_762nato_ap_description","BPRUE_Sniper_ChangeAmmoTypes762NATOAPEffect",("BPRUE_Sniper_ArmorPiercingPos15Effect","BPRUE_Sniper_RecoilPos5Effect","BPRUE_Sniper_DamagePenalty15Effect"),_ammo_icon("762x51_ap")),
            "Supersonic":("_Supersonic","sid_bprue_sniper_caliber_762nato_supersonic_name","sid_bprue_sniper_caliber_762nato_supersonic_description","BPRUE_Sniper_ChangeAmmoTypes762NATOSupersonicEffect",("RecoilPos10Effect","BPRUE_Shared_DamagePenalty10Effect","BPRUE_Sniper_FlatnessPos15Effect"),_ammo_icon("762x51_ss")),
        },
    },
    "A762NATO": {
        "target":"A762Sniper","suffix":"762Sniper","cost":5000,
        "change_effect":"ChangeCaliber762Effect","remove_effect":"BPRUE_ChangeAmmoTypesNo762NATOEffect",
        "variants":{
            "Default":("","sid_bprue_caliber_762_eastern_name","sid_bprue_sniper_caliber_762nato_to_762sniper_description","ChangeAmmoTypes762Effect",("BPRUE_DamagePos10Effect","BPRUE_ArmorPiercingPos15Effect","BPRUE_Sniper_RecoilPenalty15Effect","BPRUE_DurabilityPerShotNeg15Effect"),_ammo_icon("762x54")),
            "AP":("_AP","sid_bprue_sniper_caliber_762sniper_ap_name","sid_bprue_sniper_caliber_762sniper_ap_description","BPRUE_Sniper_ChangeAmmoTypes762SniperAPEffect",("BPRUE_Sniper_DamagePos5Effect","BPRUE_Sniper_ArmorPiercingPos25Effect","BPRUE_Sniper_RecoilPenalty20Effect","BPRUE_DurabilityPerShotNeg15Effect"),_ammo_icon("762x54_ap")),
            "Supersonic":("_Supersonic","sid_bprue_sniper_caliber_762sniper_supersonic_name","sid_bprue_sniper_caliber_762sniper_supersonic_description","BPRUE_Sniper_ChangeAmmoTypes762SniperSupersonicEffect",("BPRUE_DamagePos10Effect","BPRUE_Sniper_ArmorPiercingPos10Effect","BPRUE_Sniper_RecoilPenalty15Effect","BPRUE_DurabilityPerShotNeg15Effect","BPRUE_Sniper_FlatnessPos15Effect"),_ammo_icon("762x54_ss")),
        },
    },
}

def load_config(): return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
def module_sid(prefix,group,key): return f"{prefix}_Upgrade_BPRUE_Sniper_{group}_{key.title().replace('_','')}"

def build_upgrades(config):
    upgrades=[]
    for family in config['families'].values():
        scale=family.get('cost_scale',1.0); prefix=family['prototype_prefix']; setup=family['general_setup_sid']
        conversion=CALIBER_CONVERSIONS.get(family.get('base_caliber')) if family.get('bprue_caliber_conversion',True) else None
        if conversion:
            variant_sids=[f"{prefix}_Upgrade_BPRUE_Sniper_Caliber_{conversion['suffix']}{spec[0]}" for spec in conversion["variants"].values()]
            for spec in conversion["variants"].values():
                suffix,text,hint,ammo_effect,stats,icon=spec
                current=f"{prefix}_Upgrade_BPRUE_Sniper_Caliber_{conversion['suffix']}{suffix}"
                effects=(conversion["change_effect"],conversion["remove_effect"],ammo_effect,*stats)
                upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=setup,weapon_class='Sniper',group='Caliber',target_part='Body',text_sid=text,hint_sid=hint,image=icon,icon=CALIBER_ICON,cost=round(conversion["cost"]*scale),effects=tuple(effects),blocking_sids=tuple(x for x in variant_sids if x!=current),template_sid=TEMPLATE_SID,layout_group=f"Caliber_{conversion['target']}"))
        for group,definitions,target,vertical in GROUPS:
            group_sids=[module_sid(prefix,group,key) for key in definitions]
            for key,(cost,effects) in definitions.items():
                current=module_sid(prefix,group,key)
                upgrades.append(UpgradeDefinition(sid=current,general_setup_sid=setup,weapon_class='Sniper',group=group,target_part=target,text_sid=f'sid_bprue_sniper_{key}_name',hint_sid=f'sid_bprue_sniper_{key}_description',image=IMAGE,icon=ICON,cost=round(cost*scale),effects=tuple(effects),blocking_sids=tuple(x for x in group_sids if x!=current),vertical_position=vertical,template_sid=TEMPLATE_SID))
    return upgrades

EFFECT_LOCALIZATION={'ArmorPiercing':'bprue_armor_piercing','WeaponDamage':'bprue_damage','EffectiveFireDistance':'bprue_effective_range','Recoil':'bprue_recoil','AimingTime':'bprue_aiming_speed','Weight':'bprue_weight','FireInterval':'bprue_fire_rate','Dispersion':'bprue_accuracy','ShotRecovery':'bprue_recoil_recovery','IdleSwayX':'bprue_aiming_stability','IdleSwayY':'bprue_aiming_stability','DurabilityPerShot':'bprue_weapon_wear'}

def render_effects():
    definitions=[('BPRUE_Sniper_DamagePos5Effect','WeaponDamage','5%','Positive'),('BPRUE_Sniper_DamagePenalty15Effect','WeaponDamage','-15%','Negative'),('BPRUE_Sniper_ArmorPiercingPos10Effect','ArmorPiercing','10%','Positive'),('BPRUE_Sniper_ArmorPiercingPos15Effect','ArmorPiercing','15%','Positive'),('BPRUE_Sniper_ArmorPiercingPos25Effect','ArmorPiercing','25%','Positive'),('BPRUE_Sniper_RecoilPos5Effect','Recoil','5%','Positive'),('BPRUE_Sniper_FlatnessPos15Effect','EffectiveFireDistance','15%','Positive'),('BPRUE_Sniper_RecoilPenalty10Effect','Recoil','10%','Negative'),('BPRUE_Sniper_RecoilPenalty15Effect','Recoil','15%','Negative'),('BPRUE_Sniper_RecoilPenalty20Effect','Recoil','20%','Negative'),('BPRUE_Sniper_AimingTimePenalty10Effect','AimingTime','10%','Negative'),('BPRUE_Sniper_AimingTimePenalty15Effect','AimingTime','15%','Negative'),('BPRUE_Sniper_AimingTimePos20Effect','AimingTime','-20%','Positive'),('BPRUE_Sniper_WeightPenalty10Effect','Weight','10%','Negative'),('BPRUE_Sniper_FireIntervalPenalty10Effect','FireInterval','10%','Negative'),('BPRUE_Sniper_FireIntervalPenalty25Effect','FireInterval','25%','Negative'),('BPRUE_Sniper_DispersionPenalty15Effect','Dispersion','15%','Negative'),('BPRUE_Sniper_FireIntervalNeg15Effect','FireInterval','-15%','Positive'),('BPRUE_Sniper_FireIntervalNeg25Effect','FireInterval','-25%','Positive'),('BPRUE_Sniper_FireIntervalNeg30Effect','FireInterval','-30%','Positive'),('BPRUE_Sniper_ShotRecoveryPos25Effect','ShotRecovery','-25%','Positive'),('BPRUE_Sniper_ShotRecoveryPos30Effect','ShotRecovery','-30%','Positive'),('BPRUE_Sniper_IdleSwayXPos30Effect','IdleSwayX','-30%','Positive'),('BPRUE_Sniper_IdleSwayYPos30Effect','IdleSwayY','-30%','Positive'),('BPRUE_DurabilityPerShotNeg15Effect','DurabilityPerShot','15%','Negative')]
    lines=['// AUTO-GENERATED - Source: sniper_upgrades.json','']
    for sid,effect_type,value,beneficial in definitions:
        lines += [f'{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}',f'   SID = {sid}',f'   Type = EEffectType::{effect_type}',f'   LocalizationSID = {EFFECT_LOCALIZATION[effect_type]}',f'   ValueMin = {value}',f'   ValueMax = {value}','   bIsPermanent = true',f'   Positive = EBeneficial::{beneficial}','   ShowUpgradeEffectValue = true','   ShowUpgradeEffect = true','struct.end','']
    for sid,projectile,ammo_type in [
        ("BPRUE_Sniper_ChangeAmmoTypes762NATOAPEffect","P762NATO","ArmorPiercing"),
        ("BPRUE_Sniper_ChangeAmmoTypes762NATOSupersonicEffect","P762NATO","Supersonic"),
        ("BPRUE_Sniper_ChangeAmmoTypes762SniperAPEffect","P762Sniper","ArmorPiercing"),
        ("BPRUE_Sniper_ChangeAmmoTypes762SniperSupersonicEffect","P762Sniper","Supersonic"),
    ]:
        lines += [f'{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=ChangeAmmoTypesTemplate}}',f'   SID = {sid}','   AmmoTypeProjectiles : struct.begin','      [0] : struct.begin',f'         AmmoType = EAmmoType::{ammo_type}',f'         ProjectilePrototypeSID = {projectile}','      struct.end','   struct.end','   ShowUpgradeEffectValue = false','   ShowUpgradeEffect = false','struct.end','']
    return '\n'.join(lines)

def all_upgrade_sids(config): return [u.sid for u in build_upgrades(config)]
def main():
    config=load_config(); model=UpgradeBuildModel(); model.extend(build_upgrades(config)); model.validate()
    outputs={UPGRADE_OUTPUT:render_upgrade_prototypes(model,source='sniper_upgrades.json',template_sid=TEMPLATE_SID),EFFECT_OUTPUT:render_effects(),WEAPON_OUTPUT:render_general_setup_patch(model)}
    for path,content in outputs.items(): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf-8'); print(f'Generated {path}')
if __name__=='__main__': main()
