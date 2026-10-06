# Original tester feedback — annotated progress

> Source: `balacingBaseOverview.txt` (verbatim copy alongside this file). Original wording and ordering preserved below. Strikethrough means **a balancing response has been implemented in generator sources**, **not** that the tester's exact solution was accepted or verified in game. Other addressed-but-incomplete items carry `PARTIAL`; untouched points stay open. This is not a test sign-off.

Here's a quick overview :  
   
General Feedback  
DMRs / Snipers  
Assault Rifles (ARs)  
I haven't been able to test much with the SMGs / Pistols yet 😕  
   
   
   
1. GENERAL FEEDBACK  
   
a) UI Issues  
The UI has some issues with certain weapons, mainly in two areas :  
   
a) Module lists extending beyond the screen :  
   
Depending on the weapon, the UI can sometimes become broken. Some module lists are too long, causing certain modules to extend beyond the screen or appear right at the edge, making them difficult to select.   
   
Recommendation : I noticed that modules have a ModuleLineDirection = Right property. I think it would be worth trying to change Right to Left to see if the module lists then extend to the left instead, potentially resolving the issue.  
   
   
   
b) Pistols and unused attachment points :  
   
You have enabled several attachment points on pistols that are normally disabled (e.g. the Stock attachment point) in order to attach certain modules to them. This results in attachment points appearing to float in mid-air, with no actual connection to the weapon.  
   
Recommendation : If possible, I would recommend using only the vanilla attachment points. Combined with changes to ModuleLineDirection, I think it should be possible to achieve a consistent layout without having attachment points floating in mid-air.  
   
   
   
b) Armor Penetration modules  
I think it would be best to take the following approach, at least initially :  
   
Remove all modules that increase or decrease Armor Penetration without involving a caliber change (Soft-Target Module + Armor-Piercing Module).  
Why :  
   
Based on my own testing and the information I have been able to find, Armor Penetration is an extremely important stat that needs to be handled very carefully. Furthermore, its value and usefulness vary considerably depending on the weapon's Tier. Honestly, I think Armor Penetration is one of the few stats that would justify introducing new upgrades rather than modules. It might be worth considering implementing these as actual weapon upgrades instead of modules, reusing the game's existing assets wherever possible, to reach the desirable effect later, during Phase 3.  
   
   
   
c) Repair Costs  
Repair costs are very easy to modify, as all modules and upgrades have a RepairCostModifier = 0.2 property. This means that only 20% of the module's or upgrade's purchase price is factored into the repair cost calculation. This is therefore something that can easily be adjusted later on. Doing so would help prevent a fully upgraded Tier 1 weapon from being as effective, or almost as effective, as a Tier 3 weapon while retaining significantly lower repair costs.  
   
   
   
d) Bugs and Functionality Checks  
- Modules that increase weapon weight : These work correctly, even though the Technician's UI does not display the weight penalty. The increased weight is correctly reflected in both the inventory and the weapon's stats.  
   
- Modules that change the caliber to 7.62×39 (not to be confused with 7.62×54R) : These are essentially traps. This caliber was removed from the game in a very old patch and is no longer available. The mod does not reintroduce it either.  
   
Recommendation : Either remove these modules or add this caliber to merchants' inventories. I would strongly recommend removing them since they cannot be find on NPCs (unless the player use another mod that reintroduces it).  
   
- Caliber conversion modules for sniper rifles (SVD, SVU, Three-Line Rifle and M701 Super) : These have some strange interactions with the vanilla Barrel Hardening upgrade, which allows the use of standard ammunition instead of only high-quality ammunition.  
   
Barrel Hardening allows the use of all ammunition types, even when the caliber conversion module is supposed to restrict ammunition choices to AP or Supersonic rounds, depending on the module.  
   
These modules should either be made incompatible with Barrel Hardening or removed altogether. I would recommend removing them, for the reasons explained in point 5.  
2. DMR/SNIPERS  
   
   
   
a) VS Vintar  
   
In the current version of your mod, the VS Vintar is treated as an Assault Rifle and not a DMR/Sniper. The AS Lavina is explicitly an assault version of the VS Vintar and I think the VS Vintar should instead benefits from the DMR/Snipers modules.  
   
   
   
b) Modules  
   
To give you some context on how I approached this, I tested different combinations of modules, and I also looked at and tested each individual module and its effects across most of the weapons. My goal was to determine whether the modules actually allowed for meaningful weapon specialization, or whether some of them were simply "no-brainers" that you would always pick because they were strictly better than the alternatives.  
   
In general, the modules for DMRs and sniper rifles are quite good in concept, but there are too many ways to reduce recoil, to the point where these weapons can become better assault rifles than actual assault rifles at virtually all ranges. Overall, the modules benefit mid-range, automatic or semi-automatic DMRs (Mark 1 EMR, G3PA, SIC) much more than dedicated sniper rifles (Three-Line Rifle, SVD, SVU, M701). My idea was therefore to have one branch of modules that clearly focuses on improving the weapon's effectiveness at long range, while another branch would primarily focus on medium-range combat and moving around the battlefield.  
   
With the exception of certain unique weapons (such as CoH Luftgarde, which can be handled through its unique upgrade), I don't think DMR/sniper modules should significantly improve their effectiveness at close range, as this would encroach too heavily on the role of SMGs and Assault Rifles.  
   
I have three types of comments for the different modules :  
   
OK => No remarks. I think this module is very good, both in terms of its concept and its numbers.  
   
OP => This module is clearly overpowered and is typically a "no-brainer" that doesn't provide any real choice (these are relatively rare).  
   
OK in principle => I understand the idea behind the module, but I may have some remarks about the numbers chosen or about the types of bonuses/penalties that should be adjusted in my opinion. I will specify what I think should be changed (if I don't, it means it's just the numbers).  
   
Lightweight Stock : OK.  
~~Adjustable Stock : OP. In my opinion, it needs to be nerfed or removed altogether. It is essentially a straight buff and doesn't really offer any meaningful specialization, so I would personally remove it.~~  

> **ADDRESSED (source only)** — Adjusted Adjustable Stock instead of removing it; pending in-game validation.

Precision Stock : OP. It provides 2 instances of improved Aiming Stability and should only improve Recoil Recovery instead of Recoil.  

> **PARTIAL** — Precision Stock adjusted, but the tester's requested recoil-to-recovery replacement was not implemented.

Hardened Components : OK in principle (types of bonus/malus are fine).  
Lightweight Components : OK in principle (types of bonus/malus are fine).  
Range Configuration : Should be removed. It doesn't add anything meaningful to the role of a DMR or sniper rifle, as these weapons are already excellent at long range.  
CQB Configuration : OK in principle. In my opinion, it should come with a Recoil Recovery penalty, since Spread affects both ADS and hip-fire dispersion.  
Soft-Target Module and Armor-Piercing Module : Should be removed.  
Benchrest Setup : Needs to be reworked overall, as it provides far too many benefits to all DMRs and sniper rifles, regardless of whether they are fully automatic or not.  

> **PARTIAL** — Benchrest recoil reduced; comprehensive rework/stack test outstanding.

Like the Precision Stock, it provides 2 instances of improved Aiming Stability. It should also improve Recoil Recovery instead of Recoil. The penalties are fine as they are.  

> **PARTIAL** — Sway-axis semantics and suggested recoil-to-recovery swap still require evaluation.

Snapshooter : OK.  
~~Field Marksman : OP. In my opinion, it needs to be nerfed or removed altogether. It is essentially a straight buff and doesn't really offer any meaningful specialization, so I would personally remove it.~~  

> **ADDRESSED (source only)** — Field Marksman now has an aiming-time penalty instead of the recovery buff; retained as a meaningful option.

Recoil Control : OK.  
Precision Tuning : Doesn't really improve precision in a meaningful way. In my opinion, it should increase Flatness or reduce Damage Drop-off instead of improving Spread.  
High-Velocity Ballistics : OK in principle (types of bonus/malus are fine).  
Match Barrel : OP with current values, but OK in principle. It should come with a Durability penalty imo.  

> **PARTIAL** — Match Barrel dispersion bonus reduced; requested durability downside not implemented.

Heavy Barrel : OP with current values, but OK in principle. It should come with a Readiness penalty imo.  

> **PARTIAL** — Heavy Barrel recovery reduced; requested readiness penalty not implemented.

Rapid Action : OK.  
Precision Action : OK in principle (types of bonus/malus are fine).  
Reinforced Action : OK in principle (types of bonus/malus are fine).  
   
   
c) Caliber conversion modules  
   
In general, converting .308  weapons to 7,62R is both OP and problematic for several reasons. 7.62R ammunition is much more common than .308, which makes converting a weapon from .308 to 7.62×54R an absolute "no-brainer", especially for automatic weapons such as the Mark 1 EMR or the G3PA.  
   
Conversely, converting a weapon to .308 doesn't really have a reason to exist in the current state of the game, because .308 is the rarest ammunition type in the game. At the same time, 7.62R weapons are already extremely powerful (they are DMRs, after all), so giving them a huge damage or armor penetration buff would be a very bad idea in my opinion, as the result would inevitably be overpowered. The SIC, for example, already has 50% armor penetration and 75 damage per shot by default !  
   
In real life, .308 Winchester has slightly better ballistic characteristics than 7.62R, which fits perfectly with the game's ammunition economy : .308 should provides bonuses while 7,62R should provide maluses.  
   
On top of that, as mentioned in my first message, there is also a bug that allows players to bypass the ammunition restrictions with the vanilla Barrel Hardening upgrade. It is worth noting that the conversions work perfectly fine without Barrel Hardening.  
   
After thinking about it, I believe all of these "special" conversions should be removed. They don't add much to the game, they clearly increase damage far too much, and there is currently no real incentive for the player to use them unless once it has so many koupons that it can keep buying ammos at every merchants.  
   
Recommendation :  
   
> **PARTIAL (generator updated; in-game unverified)** — All Sniper/DMR conversion variants now inherit the same directional ballistics. AP adds +5% armor penetration and -5% damage; Supersonic adds +5% projectile speed and +5% wear per shot. The maintainer previously regenerated Default CFGs; the latest specialization changes still need regeneration and verification. The Barrel Hardening restriction issue remains open. Original tester feedback retained.

Converting a weapon to .308 should improve Velocity, Damage Drop-off (not particularly useful against humans, but very useful when hunting mutants), and Flatness. This would make the weapon even better suited for precision shooting.  
Converting a weapon to 7.62×54R should reduce Velocity, Flatness, and Damage Drop-off. In exchange, the player gains access to a much more common and cheaper ammunition type, allowing them to save money at the cost of reduced long-range effectiveness. This would give players a stronger incentive to use the conversion on weapons such as the Mark 1 EMR or G3PA rather than on something like the M701 Super.  
> **PARTIAL — AR caliber conversions (generated, not tested):** Rebalanced the existing 5.45 → 7.62×54R and 5.56 → .308 power conversions and 7.62×39 conversions, including a separate 9×39 → 7.62×39 baseline for VS Vintar. Default/AP/Supersonic (or Default/AP/Expanding) remain mutually exclusive complete conversion profiles. Unconditional damage and AP buffs were reduced, while recoil, wear, trajectory and damage drop-off trade-offs were added. The maintainer has regenerated and pushed CFGs; runtime and ammunition-economy testing remain open. The tester's recommendation to favor AR-native calibers and a different per-weapon conversion matrix was **not adopted**; neither ammo availability nor the risk of a conversion becoming a no-brainer is verified. Vanilla-owned conversions and 7.62×39 compatibility remain intentionally unchanged.

3. Assault Rifles (AR) :  
Assault rifles are already very versatile weapons, with good range, good damage, and generally good recoil and spread (there are a very few exceptions to that rule, namely the AKM-74S and the Dnipro). The current system doesn't really encourage specialization or even meaningful progression. It is an absolute no-brainer to simply take every module that reduces recoil and spread and turn any AR into a literal laser beam, allowing you to chain headshots in full auto with virtually no difficulty while still retaining the weapon's overall versatility.  
   
Like with the DMR/Snipers, in my opinion, there should almost only be two main "branches" for ARs.  
   
The first would be an Assault branch, focusing on reducing Spread, improving movement speed while aiming, Readiness, and Fire Rate. The goal of this branch would be to turn the AR into a proper assault weapon, somewhat comparable to an SMG even when firing from the hip, while still retaining some of the AR's versatility. This should come with small penalties to things such as range, bullet velocity, overall recoil, etc.  
The second would be a Long-Range branch, focusing on Aimed Accuracy (which only affects Spread while aiming), Recoil Recovery, a small amount of Recoil reduction, and Aimed Stability. This branch would improve the AR's effectiveness at medium and long range, especially when firing short bursts, but at the cost of characteristics such as weapon weight, Aiming Speed, movement speed while aiming, and the weapon's raw DPS (through a reduction in Fire Rate, which would also help in controlling recoil).  
   
   
a) Firing mode modules  
   
Precision Fire Control : In my opinion, this is a rather pointless module. ARs already have fairly low recoil when firing in semi-auto, and forcing an AR to fire exclusively in semi-auto isn't particularly interesting unless it also comes with HUGE damage boosts, like the unique Clusterf*#@ and Jagerblick ARs. However, giving the module such massive damage boosts would reduce the uniqueness of those two weapons. I think this module should therefore be removed.  
Burst Fire Control : This is more interesting, but because it gives access to full-auto, it still isn't particularly interesting as a specialization option. In my opinion, Burst Fire should instead replace Full Auto, leaving the weapon with only Semi-Auto and Burst Fire. This is the one exception where I wouldn't add an additional penalty : the penalty is already built into the loss of Full Auto.  
   
   
b) Caliber conversion modules  
   
Overall, I think that, just like with DMRs/snipers, the single generic caliber conversion should be retained instead of dividing the bonuses and penalties between three different ammunition types every time for the same reason as the DMR/Snipers.  
   
Just like with DMRs/snipers, I think you should be careful with ammo conversions. For many ARs, converting them to a DMR/sniper caliber is almost never worth it because these ammunition types are much rarer. Originally, the Dnipro could be converted to another AR round (7.62×39), but because this round was removed from the game in an old patch, it was then converted to use 7.62R, which clearly doesn't make much sense when you consider the size of the Dnipro's magazine. For example, there is absolutely no reason to ever convert the GP37 to .308 or the AKM-74S to 7,62R. Even the vanilla Dnipro caliber conversion isn't used very often from what I've seen because of how expensive the weapon becomes.  
   
For the AR family of rifles, I think we should stick to AR calibers, with a few carefully chosen exceptions to avoid making unique ARs with unique ammo conversions obsolete, such as the unique AREv (Warzsawa) or the AKM-9B.  
   
Regardless, because 5,45 ammunition is much more common than both 5,56 and 9mm (the Grom S-14/As Lavina ammo), a 5,45 conversion should provide only very minor bonuses alongside a penalty, similar to the vanilla Kharod ammo conversion. Conversely, converting a weapon to 5.56 or 9mm should provide stronger bonuses.  
   
For example :  
   
5,56mm bonuses/maluses : Similar to the Fora-221.  
9mm : +Damage (20%, for example), -Recoil, -Flatness.  
5,45 : Similar to the Kharod (+Wear & Tear, -Spread).  
Here's suggestions :  
   
AKM-74S : 5,56 conversion.  
AKMU-74S : 9mm conversion.  
AR416 : 5,45 conversion.  
GP37 : 5,56 conversion.  
Fora-221 : No change, keep it like vanilla.  
AS Lavina : No conversion. An integrally suppressed weapon doesn't really make sense with a supersonic round.  
AREv : 9mm conversion.  
VS Vintar : No conversion. An integrally suppressed weapon doesn't really make sense with a supersonic round.  
Kharod : No change, keep it like vanilla.  
Dnipro : No change, keep it like vanilla.  
   
   
d) Modules   
   
Lightweight Stock : OK.  
Stabilized Stock : OP. It should be removed. It is simply too good overall, regardless of what you want the weapon to specialize in, and clearly overshadows all the other options.  

> **PARTIAL** — AR Stabilized Stock recovery reduced; tester asked for removal, which was not adopted.

Marksman Stock : OK in principe, but needs a slight rework. It should focus on Aimed Stability and Aimed Accuracy, while keeping Aiming Speed as its penalty.  
Hardened Components : OK in principle (types of bonus/malus are fine).  
Lightweight Components : OK in principle (types of bonus/malus are fine).  
High-Speed Operation : OK in principle (types of bonus/malus are fine).  
Tuned Gas System : OK in principle but I would remove the increased Fire Rate. The module is already very, very good without it.  
High-Cyclic System and Controlled Action : These are completely redundant with High-Speed Operation and Tuned Gas System. They should be entirely reworked and renamed to match the two branches described above, if you decide to go in that direction. For example :  

> **PARTIAL** — Shared Controlled Action tuned toward precision; wholesale redesign and naming request not implemented.

Quality Pencil Barrel (Assault): +Readiness, +Slowing Spread Increase, -Recoil Recovery.  
Reinforced Heavy Barrel (Long Range): +Aimed Accuracy, +Flatness, +Damage Drop-off, -Aiming Speed, +Weight (more weight), -Speed while aiming.  
Recoil Control : OK.  
Precision Tuning : Doesn't really improve precision in a meaningful way. In my opinion, it should increase Flatness or reduce Damage Drop-off instead of improving Spread.  
~~Competition Reload System : OK in principe (I would just switch the Recoil malus to a heavy Spread malus).~~  

> **ADDRESSED (source only)** — Competition Reload recoil penalty replaced by dispersion penalty; value chosen is 5%, not the tester's suggested heavy penalty.

Reinforced Feed System : OK in principle (I would remove the bonus to Reload Speed however and switch the current bonus to Wear & Tear since the bonus to external wear & tear is straight up inferior since it doesn't always apply).  

> **PARTIAL** — Reinforced Reload speed bonus removed; wear-related behavior still needs testing.

