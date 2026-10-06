# Original feedback — annotated progress

> Source: `balacingBaseOverview.txt` (complete original feedback). This is a condensed review checklist, not a verbatim copy. ~~Strikethrough~~ = **DONE** (reviewed and resolved, including intentionally rejected proposals). Unstruck items = **OPEN** (decision or investigation pending). Gameplay validation is tracked separately; DONE does not mean tested in game.
---

I have three types of comments for the different modules :  
   
- OK => No remarks. I think this module is very good, both in terms of its concept and its numbers.   
- OP => This module is clearly overpowered and is typically a "no-brainer" that doesn't provide any real choice (these are relatively rare).  
- OK in principle => I understand the idea behind the module, but I may have some remarks about the numbers chosen or about the types of bonuses/penalties that should be adjusted in my opinion. I will specify what I think should be changed (if I don't, it means it's just the numbers).  

---
  
# 1. GENERAL FEEDBACK  
   
## a) UI Issues  
The UI has some issues with certain weapons, mainly in two areas.
   
### a) Module lists extending beyond the screen :  
   
Depending on the weapon, the UI can sometimes become broken. Some module lists are too long, causing certain modules to extend beyond the screen or appear right at the edge, making them difficult to select.   
   
Recommendation : I noticed that modules have a ModuleLineDirection = Right property. I think it would be worth trying to change Right to Left to see if the module lists then extend to the left instead, potentially resolving the issue.  
   
### b) Pistols and unused attachment points :  
   
You have enabled several attachment points on pistols that are normally disabled (e.g. the Stock attachment point) in order to attach certain modules to them. This results in attachment points appearing to float in mid-air, with no actual connection to the weapon.  
   
Recommendation : If possible, I would recommend using only the vanilla attachment points. Combined with changes to ModuleLineDirection, I think it should be possible to achieve a consistent layout without having attachment points floating in mid-air.  
   
## b) Armor Penetration modules  
I think it would be best to take the following approach, at least initially :  
   
~~Remove all modules that increase or decrease Armor Penetration without involving a caliber change (Soft-Target Module + Armor-Piercing Module).~~  
Why:  Based on my own testing and the information I have been able to find, Armor Penetration is an extremely important stat that needs to be handled very carefully. Furthermore, its value and usefulness vary considerably depending on the weapon's Tier. Honestly, I think Armor Penetration is one of the few stats that would justify introducing new upgrades rather than modules. It might be worth considering implementing these as actual weapon upgrades instead of modules, reusing the game's existing assets wherever possible, to reach the desirable effect later, during Phase 3.  
   
> **DONE (generator only)** — Preserved both module upgrade SIDs and their mutual exclusion instead of removing the slots. Soft-Target is now an experimental wounding profile (+10% BleedingChancePerShot, −10% CoverPiercing); Armor-Piercing is renamed **Barrier Module** (+20% CoverPiercing, −10% WeaponDamage). Neither changes ArmorPiercing. **OPEN gameplay validation:** verify whether bleeding chance percentages are multiplicative, additive or absolute, including interaction with ammunition and baseline bleeding. Generated CFGs and in-game testing pending.

## c) Repair Costs  
Repair costs are very easy to modify, as all modules and upgrades have a RepairCostModifier = 0.2 property. This means that only 20% of the module's or upgrade's purchase price is factored into the repair cost calculation. This is therefore something that can easily be adjusted later on. Doing so would help prevent a fully upgraded Tier 1 weapon from being as effective, or almost as effective, as a Tier 3 weapon while retaining significantly lower repair costs.  
   
## d) Bugs and Functionality Checks  
- ~~Modules that increase weapon weight : These work correctly, even though the Technician's UI does not display the weight penalty. The increased weight is correctly reflected in both the inventory and the weapon's stats.~~  
   
- ~~Modules that change the caliber to 7.62×39 (not to be confused with 7.62×54R) : These are essentially traps. This caliber was removed from the game in a very old patch and is no longer available. The mod does not reintroduce it either. **Recommendation:** Either remove these modules or add this caliber to merchants' inventories. I would strongly recommend removing them since they cannot be find on NPCs (unless the player use another mod that reintroduces it).~~

> **DONE** — 7.62×39 support remains for compatibility with other mods. No merchant injection is planned; the missing vanilla ammunition supply is a known limitation.  
   
- ~~Caliber conversion modules for sniper rifles (SVD, SVU, Three-Line Rifle and M701 Super) : These have some strange interactions with the vanilla Barrel Hardening upgrade, which allows the use of standard ammunition instead of only high-quality ammunition. Barrel Hardening allows the use of all ammunition types, even when the caliber conversion module is supposed to restrict ammunition choices to AP or Supersonic rounds, depending on the module. These modules should either be made incompatible with Barrel Hardening or removed altogether. I would recommend removing them, for the reasons explained in point 5.~~

> **DONE (source-level fix, not gameplay-validated)** — Kept the conversions and added bidirectional blocking against the identified terminal Vanilla ammunition-changing upgrades: SVD/SVU/M701 `Barrel_3_2`, Three-Line `Barrel_3`. All three BPRUE conversion variants (Default/AP/Supersonic) block the respective Vanilla SID; a separate generated Vanilla `bpatch` adds the reciprocal blockers without directly editing Vanilla reference files. The inspected Vanilla chains show no direct successors for these terminal upgrades. **OPEN validation:** unified CFG regeneration, patch merging (especially preserving existing Vanilla blockers), installation order in both directions, reload/save persistence, and actual ammunition restrictions in game. The exact localized Barrel Hardening label was not independently verified.  

# 2. DMR/SNIPERS     
   
## a) VS Vintar  
   
~~In the current version of your mod, the VS Vintar is treated as an Assault Rifle and not a DMR/Sniper. The AS Lavina is explicitly an assault version of the VS Vintar and I think the VS Vintar should instead benefits from the DMR/Snipers modules.~~

> **DONE (generator sources)** — VS Vintar moved to Sniper/DMR modules, while AS Lavina remains AR. Merc unique now follows the Vintar Sniper family. The existing Vintar 7.62×39 conversion SIDs and profiles are retained; AR specialization slots are intentionally removed (breaking change for saves). **OPEN validation:** unified CFG regeneration, Merc unique behavior, save compatibility and gameplay checks.  
   
## b) Modules  
   
To give you some context on how I approached this, I tested different combinations of modules, and I also looked at and tested each individual module and its effects across most of the weapons. My goal was to determine whether the modules actually allowed for meaningful weapon specialization, or whether some of them were simply "no-brainers" that you would always pick because they were strictly better than the alternatives.  
   
In general, the modules for DMRs and sniper rifles are quite good in concept, but there are too many ways to reduce recoil, to the point where these weapons can become better assault rifles than actual assault rifles at virtually all ranges. Overall, the modules benefit mid-range, automatic or semi-automatic DMRs (Mark 1 EMR, G3PA, SIC) much more than dedicated sniper rifles (Three-Line Rifle, SVD, SVU, M701). My idea was therefore to have one branch of modules that clearly focuses on improving the weapon's effectiveness at long range, while another branch would primarily focus on medium-range combat and moving around the battlefield.  
   
With the exception of certain unique weapons (such as CoH Luftgarde, which can be handled through its unique upgrade), I don't think DMR/sniper modules should significantly improve their effectiveness at close range, as this would encroach too heavily on the role of SMGs and Assault Rifles.  
   
- ~~Lightweight Stock : OK.~~  
- ~~Adjustable Stock : OP. In my opinion, it needs to be nerfed or removed altogether. It is essentially a straight buff and doesn't really offer any meaningful specialization, so I would personally remove it.~~  

> **DONE** — Adjusted Adjustable Stock instead of removing it; pending in-game validation.

- ~~Precision Stock : OP. It provides 2 instances of improved Aiming Stability and should only improve Recoil Recovery instead of Recoil.~~  

> **DONE** — Precision Stock was rebalanced with +30% sway stability on both axes, +20% recoil control and −15% aiming speed. Replacing recoil control with recovery was not adopted. No further source change planned before gameplay testing.

- ~~Hardened Components : OK in principle (types of bonus/malus are fine).~~  
- ~~Lightweight Components : OK in principle (types of bonus/malus are fine).~~  
- ~~Range Configuration : Should be removed. It doesn't add anything meaningful to the role of a DMR or sniper rifle, as these weapons are already excellent at long range.~~

> **DONE** — Kept the existing upgrade SID and redesigned the DMR/Sniper effects toward long range: +15% flatness, +10% damage drop-off length, −10% aiming speed (generator only).  
- ~~CQB Configuration : OK in principle. In my opinion, it should come with a Recoil Recovery penalty, since Spread affects both ADS and hip-fire dispersion.~~

> **DONE** — Added a 10% recoil-recovery penalty for DMR/Sniper; existing upgrade SID retained (generator only).  
- ~~Soft-Target Module and Armor-Piercing Module : Should be removed.~~ See the general Armor Penetration decision above; retained as distinct wounding/cover modules, not AP modifiers.  
- ~~Benchrest Setup : Needs to be reworked overall, as it provides far too many benefits to all DMRs and sniper rifles, regardless of whether they are fully automatic or not. Like the Precision Stock, it provides 2 instances of improved Aiming Stability. It should also improve Recoil Recovery instead of Recoil. The penalties are fine as they are.~~   

> **DONE** — Benchrest recoil benefit reduced to 10%; retained the current stability/recoil specialization and penalties instead of adopting the proposed full redesign. Effect stacking and in-game behavior require separate validation.
 
> **DONE** — The current Benchrest profile keeps stability on both sway axes and recoil control rather than swapping to recovery. No further balance changes planned before gameplay testing.

- ~~Snapshooter : OK.~~  
- ~~Field Marksman : OP. In my opinion, it needs to be nerfed or removed altogether. It is essentially a straight buff and doesn't really offer any meaningful specialization, so I would personally remove it.~~  

> **DONE** — Field Marksman now has an aiming-time penalty instead of the recovery buff; retained as a meaningful option.

- ~~Recoil Control : OK.~~  
- ~~Precision Tuning : Doesn't really improve precision in a meaningful way. In my opinion, it should increase Flatness or reduce Damage Drop-off instead of improving Spread.~~

> **DONE** — DMR/Sniper now gains +10% flatness and +10% damage drop-off length instead of spread; −8% recoil control retained (generator only).  
- ~~High-Velocity Ballistics : OK in principle (types of bonus/malus are fine).~~  
- ~~Match Barrel : OP with current values, but OK in principle. It should come with a Durability penalty imo.~~  

> **DONE** — Match Barrel dispersion benefit reduced to 15%; aiming-time penalty retained at 10%. A durability downside was not adopted. Gameplay validation remains.

- ~~Heavy Barrel : OP with current values, but OK in principle. It should come with a Readiness penalty imo.~~  

> **DONE** — Heavy Barrel recovery reduced to 10%; weight and aiming-time penalties remain. An additional readiness penalty was not adopted. Gameplay validation remains.

- ~~Rapid Action : OK.~~  
- ~~Precision Action : OK in principle (types of bonus/malus are fine).~~  
- ~~Reinforced Action : OK in principle (types of bonus/malus are fine).~~  
   
   
## c) Caliber conversion modules  
In general, converting .308  weapons to 7,62R is both OP and problematic for several reasons. 7.62R ammunition is much more common than .308, which makes converting a weapon from .308 to 7.62×54R an absolute "no-brainer", especially for automatic weapons such as the Mark 1 EMR or the G3PA.  
   
Conversely, converting a weapon to .308 doesn't really have a reason to exist in the current state of the game, because .308 is the rarest ammunition type in the game. At the same time, 7.62R weapons are already extremely powerful (they are DMRs, after all), so giving them a huge damage or armor penetration buff would be a very bad idea in my opinion, as the result would inevitably be overpowered. The SIC, for example, already has 50% armor penetration and 75 damage per shot by default !  
   
In real life, .308 Winchester has slightly better ballistic characteristics than 7.62R, which fits perfectly with the game's ammunition economy : .308 should provides bonuses while 7,62R should provide maluses.  
   
On top of that, as mentioned in my first message, there is also a bug that allows players to bypass the ammunition restrictions with the vanilla Barrel Hardening upgrade. It is worth noting that the conversions work perfectly fine without Barrel Hardening.  
   
After thinking about it, I believe all of these "special" conversions should be removed. They don't add much to the game, they clearly increase damage far too much, and there is currently no real incentive for the player to use them unless once it has so many koupons that it can keep buying ammos at every merchants.  
   
**Recommendation:** 
Converting a weapon to .308 should improve Velocity, Damage Drop-off (not particularly useful against humans, but very useful when hunting mutants), and Flatness. This would make the weapon even better suited for precision shooting.  
Converting a weapon to 7.62×54R should reduce Velocity, Flatness, and Damage Drop-off. In exchange, the player gains access to a much more common and cheaper ammunition type, allowing them to save money at the cost of reduced long-range effectiveness. This would give players a stronger incentive to use the conversion on weapons such as the Mark 1 EMR or G3PA rather than on something like the M701 Super.

> **DONE** — All Sniper/DMR conversion variants now inherit the same directional ballistics. AP adds +5% armor penetration and -5% damage; Supersonic adds +5% projectile speed and +5% wear per shot. The maintainer previously regenerated Default CFGs; the conversion CFGs have since been regenerated and pushed; in-game verification remains open. A reciprocal source-level exclusion patch for the Barrel Hardening interaction is committed, but regeneration and in-game verification remain open. Original feedback retained.

# 3. Assault Rifles (AR) :  
Assault rifles are already very versatile weapons, with good range, good damage, and generally good recoil and spread (there are a very few exceptions to that rule, namely the AKM-74S and the Dnipro). The current system doesn't really encourage specialization or even meaningful progression. It is an absolute no-brainer to simply take every module that reduces recoil and spread and turn any AR into a literal laser beam, allowing you to chain headshots in full auto with virtually no difficulty while still retaining the weapon's overall versatility.  
   
Like with the DMR/Snipers, in my opinion, there should almost only be two main "branches" for ARs.  
   
The first would be an Assault branch, focusing on reducing Spread, improving movement speed while aiming, Readiness, and Fire Rate. The goal of this branch would be to turn the AR into a proper assault weapon, somewhat comparable to an SMG even when firing from the hip, while still retaining some of the AR's versatility. This should come with small penalties to things such as range, bullet velocity, overall recoil, etc.  
The second would be a Long-Range branch, focusing on Aimed Accuracy (which only affects Spread while aiming), Recoil Recovery, a small amount of Recoil reduction, and Aimed Stability. This branch would improve the AR's effectiveness at medium and long range, especially when firing short bursts, but at the cost of characteristics such as weapon weight, Aiming Speed, movement speed while aiming, and the weapon's raw DPS (through a reduction in Fire Rate, which would also help in controlling recoil).  
   
## a) Firing mode modules  
   
- ~~Precision Fire Control : In my opinion, this is a rather pointless module. ARs already have fairly low recoil when firing in semi-auto, and forcing an AR to fire exclusively in semi-auto isn't particularly interesting unless it also comes with HUGE damage boosts, like the unique Clusterf*#@ and Jagerblick ARs. However, giving the module such massive damage boosts would reduce the uniqueness of those two weapons. I think this module should therefore be removed.~~  
- ~~Burst Fire Control : This is more interesting, but because it gives access to full-auto, it still isn't particularly interesting as a specialization option. In my opinion, Burst Fire should instead replace Full Auto, leaving the weapon with only Semi-Auto and Burst Fire. This is the one exception where I wouldn't add an additional penalty : the penalty is already built into the loss of Full Auto.~~

> **DONE** — Precision Fire Control is retained as a semi-auto-only handling specialization (15% lower maximum dispersion, 10% faster recoil recovery, 10% slower aiming movement), rather than removed. Burst Fire Control now replaces Full Auto with Semi + Burst. Its existing 5% recoil benefit and 10% additional wear remain, so the proposal to use mode loss as the sole trade-off was not adopted. Regeneration and in-game checks are pending.  
   
## b) Caliber conversion modules  
   
~~Overall, I think that, just like with DMRs/snipers, the single generic caliber conversion should be retained instead of dividing the bonuses and penalties between three different ammunition types every time for the same reason as the DMR/Snipers.~~

> **DONE** — Keep Default/AP/Supersonic (and 7.62×39 Expanding) as mutually exclusive full conversion choices. All variants now inherit the same directional baseline rather than each having an unrelated set of stats. They are not cumulative modules; ammo access remains specialized. Generated output still needs in-game verification.  
   
~~Just like with DMRs/snipers, I think you should be careful with ammo conversions. For many ARs, converting them to a DMR/sniper caliber is almost never worth it because these ammunition types are much rarer. Originally, the Dnipro could be converted to another AR round (7.62×39), but because this round was removed from the game in an old patch, it was then converted to use 7.62R, which clearly doesn't make much sense when you consider the size of the Dnipro's magazine. For example, there is absolutely no reason to ever convert the GP37 to .308 or the AKM-74S to 7,62R. Even the vanilla Dnipro caliber conversion isn't used very often from what I've seen because of how expensive the weapon becomes.~~

> **DONE** — Reduced unconditional damage/AP buffs in existing 5.45 → 7.62×54R and 5.56 → .308 conversions, with recoil/wear and trajectory/drop-off trade-offs. Retained the conversions for AK74, G37, M16 and Arev instead of removing or replacing them. The reported rarity and actual cost-effectiveness of each caliber require gameplay testing. Dnipro's vanilla conversion remains untouched.  
   
~~For the AR family of rifles, I think we should stick to AR calibers, with a few carefully chosen exceptions to avoid making unique ARs with unique ammo conversions obsolete, such as the unique AREv (Warzsawa) or the AKM-9B.~~

> **DONE** — No conversion-matrix redesign in this pass. Existing BPRUE target calibers and special cases remain, as do vanilla ownership exclusions. The preference for only AR-native calibers is not implemented; unique and magazine plausibility should be revisited only if testing identifies a problem.  
   
~~Regardless, because 5,45 ammunition is much more common than both 5,56 and 9mm (the Grom S-14/As Lavina ammo), a 5,45 conversion should provide only very minor bonuses alongside a penalty, similar to the vanilla Kharod ammo conversion. Conversely, converting a weapon to 5.56 or 9mm should provide stronger bonuses.~~

> **DONE** — We intentionally retained the existing caliber matrix rather than adding the proposed 5.45/5.56/9mm conversions. The 7.62×39 conversion remains supported for mod compatibility without merchant ammunition. Ammo economy and in-game effectiveness require separate validation.  
   
~~For example :~~  
- ~~5,56mm bonuses/maluses : Similar to the Fora-221.~~  
- ~~9mm : +Damage (20%, for example), -Recoil, -Flatness.~~  
- ~~5,45 : Similar to the Kharod (+Wear & Tear, -Spread).~~  

~~Here's suggestions:~~  
- ~~AKM-74S : 5,56 conversion.~~  
- ~~AKMU-74S : 9mm conversion.~~  
- ~~AR416 : 5,45 conversion.~~  
- ~~GP37 : 5,56 conversion.~~  
- ~~Fora-221 : No change, keep it like vanilla.~~  
- ~~AS Lavina : No conversion. An integrally suppressed weapon doesn't really make sense with a supersonic round.~~  
- ~~AREv : 9mm conversion.~~  
- ~~VS Vintar : No conversion. An integrally suppressed weapon doesn't really make sense with a supersonic round.~~  
- ~~Kharod : No change, keep it like vanilla.~~  
- ~~Dnipro : No change, keep it like vanilla.~~

> **DONE — Per-weapon disposition (source configuration, not runtime verification):** AKM-74S/AK74 retains 7.62×54R and optional 7.62×39 rather than the proposed 5.56; AKMU-74S is not added to the AR conversion configuration; AR416/M16 retains .308 rather than 5.45; GP37/G37 retains .308 rather than 5.56. Fora-221, Kharod and Dnipro retain vanilla conversion ownership. AS Lavina remains without BPRUE conversion; AREv retains .308 rather than proposed 9mm; VS Vintar retains its explicit 7.62×39 exception instead of removing it. **No changes to these choices were made in this balancing pass.**  
   
## d) Modules   
   
- ~~Lightweight Stock : OK.~~  
- ~~Stabilized Stock : OP. It should be removed. It is simply too good overall, regardless of what you want the weapon to specialize in, and clearly overshadows all the other options.~~  

> **DONE** — Stabilized Stock was rebalanced rather than removed: +15% recoil control, +10% recoil recovery, −10% aiming speed. No further source change planned before gameplay testing.

- ~~Marksman Stock : OK in principe, but needs a slight rework. It should focus on Aimed Stability and Aimed Accuracy, while keeping Aiming Speed as its penalty.~~

> **DONE** — Already provides +20% sway stability on both axes, +15% maximum-dispersion accuracy and −15% aiming speed. Review considered complete pending gameplay testing.  

- ~~Hardened Components : OK in principle (types of bonus/malus are fine).~~  
- ~~Lightweight Components : OK in principle (types of bonus/malus are fine).~~  
- ~~High-Speed Operation : OK in principle (types of bonus/malus are fine).~~  
~~- Tuned Gas System : OK in principle but I would remove the increased Fire Rate. The module is already very, very good without it.~~  
~~- High-Cyclic System and Controlled Action : These are completely redundant with High-Speed Operation and Tuned Gas System. They should be entirely reworked and renamed to match the two branches described above, if you decide to go in that direction.~~ 

> **DONE (source only)** — Preserve two independently exclusive groups, FireRate and Shared Action, with CQB vs. mid/long-range options. High-Speed: −12% FireInterval, +15% recoil, +20% wear; Tuned Gas: −5% FireInterval, +5% recoil control, +15% recovery, +10% wear; AR High-Cyclic: −8% FireInterval, +10% accuracy, +10% recoil, +8% wear; AR Controlled Action: +10% FireInterval, +15% accuracy, +10% recovery. Shared Action changes apply to AR only; SIDs/blockers unchanged. Fire rate deliberately retained as a BPRUE differentiator. Generated CFGs and gameplay validation pending.

- ~~Recoil Control : OK.~~  
~~Precision Tuning : Doesn't really improve precision in a meaningful way. In my opinion, it should increase Flatness or reduce Damage Drop-off instead of improving Spread.~~  
> **DONE (source only)** — AR Precision Tuning now grants +10% flatness and +5% damage drop-off length instead of −15% dispersion; +8% recoil penalty retained. Recoil Control and Controlled Action remain unchanged. AR-only override and description; CFG regeneration and in-game validation pending.

~~Competition Reload System : OK in principe (I would just switch the Recoil malus to a heavy Spread malus).~~  

> **DONE** — Competition Reload recoil penalty replaced by dispersion penalty; value chosen is 5%, not the proposed heavy penalty.

- ~~Reinforced Feed System : OK in principle (I would remove the bonus to Reload Speed however and switch the current bonus to Wear & Tear since the bonus to external wear & tear is straight up inferior since it doesn't always apply).~~  

> **DONE** — Reinforced Feed no longer grants reload speed; its profile now uses +20% durability per shot and a 5% fire-interval penalty. Gameplay validation remains.

# 4. SMG :

> **DONE** — M10, Bucket and Zubr Default/AP/Expanding variants now share complete weapon-specific baseline profiles; AP adds +5% armor penetration, and Expanding relies on ammo modifiers. This is a proactive balancing pass, **not** a verified resolution of detailed SMG feedback (the original feedback notes limited SMG testing). Generated CFGs, ammo economy and in-game behavior still require validation.
