from __future__ import annotations
import json
from pathlib import Path

SCRIPT_DIR=Path(__file__).resolve().parent
PYTHON_ROOT=SCRIPT_DIR.parents[1]
CONTENT_ROOT=PYTHON_ROOT.parent
CONFIG_PATH=SCRIPT_DIR/'shotgun_upgrades.json'
UPGRADE_OUTPUT=CONTENT_ROOT/'GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_ShotgunUpgradePrototypes.cfg'
EFFECT_OUTPUT=CONTENT_ROOT/'GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_ShotgunEffectPrototypes.cfg'
WEAPON_OUTPUT=CONTENT_ROOT/'GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE_ShotgunModules.cfg'

PATTERN={
 'breacher':('Breaching Barrel','Built for room clearing: 16 buckshot pellets and a much wider pattern, but 15% shorter effective falloff distance.',2800,['BPRUE_SG_FractionCount16Effect','DispersionNeg40Effect','BPRUE_SG_DistanceDropOffNeg15Effect']),
 'field_choke':('Field Choke','A versatile choke keeping the standard 12-pellet load while tightening spread by 15% and extending falloff distance by 10%.',3000,['BPRUE_SG_FractionCount12Effect','DispersionPos15Effect','DistanceDropOffLengthPos10Effect']),
 'full_choke':('Full Choke','A long-range setup using 10 pellets in a 30% tighter pattern with 20% longer falloff distance.',3200,['BPRUE_SG_FractionCount10Effect','DispersionPos30Effect','DistanceDropOffLengthPos20Effect'])}
ACTION={
 'high_speed':('High-Speed Action','Cuts the firing cycle by 20%, but increases recoil by 15% and weapon wear by 20%.',3200,['BPRUE_FireIntervalNeg20Effect','BPRUE_SG_RecoilPenalty15Effect','BPRUE_DurabilityPerShotNeg20Effect']),
 'tuned':('Tuned Action','Cuts the firing cycle by 10% and reduces recoil by 10%, at the cost of 10% increased weapon wear.',3000,['BPRUE_FireIntervalNeg10Effect','RecoilDown10Effect','BPRUE_DurabilityPerShotNeg10Effect']),
 'reinforced':('Reinforced Action','Slows the firing cycle by 10% in exchange for 15% less recoil and 20% faster recoil recovery.',3000,['BPRUE_SG_FireIntervalPos10Effect','RecoilDown15Effect','ShotRecoveryPos20Effect'])}
FEED={
 'extended':('Extended Feed System','Increases ammunition capacity by 25%, but adds 10% weapon weight and makes reloads 10% slower.',3000,['BPRUE_SG_AmmoCapacityPos25Effect','BPRUE_SG_WeightPos10Effect','BPRUE_SG_ReloadingTimePos10Effect']),
 'competition':('Competition Feed System','Speeds reloads by 20%, but reduces ammunition capacity by 20%.',2800,['BPRUE_ReloadingTimeNeg20Effect','BPRUE_SG_AmmoCapacityNeg20Effect']),
 'tactical':('Tactical Feed System','Increases ammunition capacity by 10% and speeds reloads by 10%, but adds 5% weapon weight.',3000,['BPRUE_SG_AmmoCapacityPos10Effect','BPRUE_ReloadingTimeNeg10Effect','BPRUE_SG_WeightPos5Effect'])}
TOZ_FEED={
 'extended':('Reinforced Breech','Strengthens the breech and improves recoil control by 15% with 20% faster recovery, but reloads take 10% longer.',2400,['RecoilDown15Effect','ShotRecoveryPos20Effect','BPRUE_SG_ReloadingTimePos10Effect']),
 'competition':('Competition Extractors','Speeds the TOZ reload cycle by 20%, but increases recoil by 10%.',2200,['BPRUE_ReloadingTimeNeg20Effect','BPRUE_SG_RecoilPenalty10Effect']),
 'tactical':('Lightweight Furniture','Cuts weapon weight by 10% and improves aiming speed by 15%, but increases recoil by 10%.',2300,['WeightDown10Effect','AimingTimePos15Effect','BPRUE_SG_RecoilPenalty10Effect'])}

def cfg(): return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
def sid(prefix,group,key): return f'{prefix}_Upgrade_BPRUE_SG_{group.title()}_{key.title().replace("_","")}'
def modules_for(name,fam):
 out=[]; scale=fam.get('cost_scale',1)
 for group,defs in [('Pattern',PATTERN),('Action',ACTION),('Feeding',TOZ_FEED if fam['feeding_mode']=='break' else FEED)]:
  keys=list(defs)
  for key in keys:
   title,hint,cost,effects=defs[key]
   out.append({'sid':sid(fam['prototype_prefix'],group,key),'group':group,'key':key,'title':title,'hint':hint,'cost':round(cost*scale),'effects':effects,'block':[sid(fam['prototype_prefix'],group,k) for k in keys if k!=key]})
 return out

def render_upgrade(config):
 lines=['// AUTO-GENERATED - Source: shotgun_upgrades.json','','BPRUE_ShotgunModuleTemplate : struct.begin {refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}','   SID = BPRUE_ShotgunModuleTemplate','   IsModification = true','struct.end','']
 for name,fam in config['families'].items():
  for m in modules_for(name,fam):
   target='EUpgradeTargetPartType::Barrel' if m['group']=='Pattern' else 'EUpgradeTargetPartType::Body'
   lines += [f"{m['sid']} : struct.begin {{refkey=BPRUE_ShotgunModuleTemplate}}",f"   SID = {m['sid']}",f"   Text = sid_bprue_sg_{m['group'].lower()}_{m['key']}_name",f"   Hint = sid_bprue_sg_{m['group'].lower()}_{m['key']}_description","   Image = Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Weapons/Shotgun/SPSA/Barrel/Upgrade/T_SPAS_Upg_a_1.T_SPAS_Upg_a_1'","   Icon = Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/T_PDA_Upgrades_Icon_Recoil.T_PDA_Upgrades_Icon_Recoil'",f"   BaseCost = {m['cost']}","   VerticalPosition = EUpgradeVerticalPosition::Top",f"   UpgradeTargetPart = {target}","   EffectPrototypeSIDs : struct.begin"]
   lines += [f'      [{i}] = {e}' for i,e in enumerate(m['effects'])]
   lines += ['   struct.end','   BlockingUpgradePrototypeSIDs : struct.begin']+[f'      [{i}] = {b}' for i,b in enumerate(m['block'])]+['   struct.end','struct.end','']
 return '\n'.join(lines)

def render_effects():
 return '''// AUTO-GENERATED - Source: shotgun_upgrades.json

BPRUE_SG_FractionCount16Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_FractionCount16Effect
   Type = EEffectType::FractionCount
   ValueMin = 16
   ValueMax = 16
   AmmoType = EAmmoType::Default
   bIsPermanent = true
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
   ValueMin = -15%
   ValueMax = -15%
   Positive = EBeneficial::Negative
struct.end
BPRUE_SG_RecoilPenalty15Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_RecoilPenalty15Effect
   Type = EEffectType::Recoil
   ValueMin = 15%
   ValueMax = 15%
   bIsPermanent = true
   Positive = EBeneficial::Negative
struct.end
BPRUE_SG_RecoilPenalty10Effect : struct.begin {refkey=BPRUE_SG_RecoilPenalty15Effect}
   SID = BPRUE_SG_RecoilPenalty10Effect
   ValueMin = 10%
   ValueMax = 10%
struct.end
BPRUE_SG_FireIntervalPos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_FireIntervalPos10Effect
   Type = EEffectType::FireInterval
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
struct.end
BPRUE_SG_AmmoCapacityPos25Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_AmmoCapacityPos25Effect
   Type = EEffectType::AmmoCapacity
   ValueMin = 25%
   ValueMax = 25%
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end
BPRUE_SG_AmmoCapacityPos10Effect : struct.begin {refkey=BPRUE_SG_AmmoCapacityPos25Effect}
   SID = BPRUE_SG_AmmoCapacityPos10Effect
   ValueMin = 10%
   ValueMax = 10%
struct.end
BPRUE_SG_AmmoCapacityNeg20Effect : struct.begin {refkey=BPRUE_SG_AmmoCapacityPos25Effect}
   SID = BPRUE_SG_AmmoCapacityNeg20Effect
   ValueMin = -20%
   ValueMax = -20%
   Positive = EBeneficial::Negative
struct.end
BPRUE_SG_WeightPos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_WeightPos10Effect
   Type = EEffectType::WeaponItemWeight
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
struct.end
BPRUE_SG_WeightPos5Effect : struct.begin {refkey=BPRUE_SG_WeightPos10Effect}
   SID = BPRUE_SG_WeightPos5Effect
   ValueMin = 5%
   ValueMax = 5%
struct.end
BPRUE_SG_ReloadingTimePos10Effect : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_SG_ReloadingTimePos10Effect
   Type = EEffectType::ReloadingTime
   ValueMin = 10%
   ValueMax = 10%
   bIsPermanent = true
   Positive = EBeneficial::Negative
struct.end
'''

def render_weapons(config):
 lines=['// AUTO-GENERATED - Source: shotgun_upgrades.json','']
 for name,fam in config['families'].items():
  lines += [f"{fam['general_setup_sid']} : struct.begin {{bpatch}}","   UpgradePrototypeSIDs : struct.begin {bpatch}"]
  for m in modules_for(name,fam): lines.append(f"      [*] = {m['sid']}")
  lines += ['   struct.end','struct.end','']
 return '\n'.join(lines)

def main():
 c=cfg(); UPGRADE_OUTPUT.parent.mkdir(parents=True,exist_ok=True); EFFECT_OUTPUT.parent.mkdir(parents=True,exist_ok=True); WEAPON_OUTPUT.parent.mkdir(parents=True,exist_ok=True)
 UPGRADE_OUTPUT.write_text(render_upgrade(c),encoding='utf8'); EFFECT_OUTPUT.write_text(render_effects(),encoding='utf8'); WEAPON_OUTPUT.write_text(render_weapons(c),encoding='utf8')
 print('Generated shotgun specialization CFGs')
if __name__=='__main__': main()
