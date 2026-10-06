# Changelog

Notable changes to BPR Upgrades Expanded are recorded here, independently of design proposals and investigation notes.

This file tracks **implemented changes**, not planned features. Entries under **Unreleased** describe source changes on the current development branch; they are **not yet part of a published release**. Generated game CFGs and in-game validation may still be pending.

## [Unreleased]

### Changed
- DMR/Sniper module profiles (generator only): Range Configuration, CQB Configuration and Precision Tuning now use sniper-specific effect bundles. Existing upgrade SIDs and blocking remain intact; regeneration and in-game save verification pending.
- AR fire-control specializations (generator only): Burst replaces automatic with semi-auto + burst; Precision retains semi-auto only, trades former damage/AP bonuses for +15% maximum-dispersion accuracy, +10% recoil recovery and -10% aiming movement. Localization updated; regeneration and in-game verification pending.
- SMG conversion specializations (generator only): M10, Bucket and Zubr variants inherit full Default profiles. AP adds 5% armor penetration; Expanding uses ammunition modifiers. Existing conversion choices and restrictions remain intact. Localization updated; regeneration and testing pending.
- **AR caliber conversions (generator only):** Added complete shared Default/AP/Supersonic profiles for 5.45 to 7.62x54R and 5.56 to .308, and Default/AP/Expanding for 7.62x39. Reduced unconditional damage/AP gains and introduced trajectory, damage-drop-off, recoil and wear trade-offs. VS Vintar (9x39 to 7.62x39) uses a separate baseline. Ammo restrictions, variant blocking and vanilla-owned conversions remain unchanged. Updated EN/RU/ZH descriptions; regenerated and pushed by maintainer; in-game validation pending.
- **Sniper/DMR caliber specializations (generator only):** AP and Supersonic conversions now inherit the complete directional Default ballistic profile while retaining their own ammo-type restrictions and mutual blocking. AP adds +5% armor penetration and -5% damage; Supersonic adds +5% projectile speed and +5% wear per shot (without redundant flatness buffs). Updated all six caliber-conversion descriptions (EN/RU/ZH). regenerated and pushed by maintainer; in-game validation pending.
- **Sniper/DMR Default caliber conversions:** Reworked 7.62x54R to .308 (+10% velocity, +10% flatness, +15% damage drop-off length, +5% recoil control) and .308 to 7.62x54R (-10% velocity, -10% flatness, -15% drop-off length, 10% recoil penalty, 10% wear per shot penalty). Removed Default damage/AP modifiers; AP and Supersonic subsequently rebalanced as described above. In-game validation pending.
- **Sniper / DMR – Field Marksman:** Replaced the +10% shot-recovery bonus with a 10% aiming-time penalty to introduce a meaningful trade-off.
- **Sniper / DMR – Adjustable Stock:** Removed the +10% recoil-control bonus. Aiming stability and aimed movement benefits remain.
- **Sniper / DMR – Benchrest:** Reduced recoil-control bonus from +15% to +10%.
- **Sniper / DMR – Precision Stock:** Removed the +20% shot-recovery bonus. Stability, recoil control and slower aiming remain.
- **Assault rifles – Stabilized Stock:** Reduced shot-recovery bonus from +20% to +10%; other effects remain unchanged.
- **Assault rifles – Balanced Fire Rate:** Reduced shot-recovery bonus from +20% to +10%.
- **Assault rifles – Competition Reload:** Replaced the 15% recoil penalty with the existing 5% dispersion penalty; the 20% faster reload remains.
- **Assault rifles – Reinforced Reload:** Removed the 10% faster reload bonus; reduced weapon wear per shot and slower firing cycle remain.
- **Sniper / DMR – Match Barrel:** Reduced dispersion-improvement bonus from +25% to +15%.
- **Sniper / DMR – Heavy Barrel:** Reduced shot-recovery bonus from +20% to +10%.
- **SMGs / Assault rifles – Controlled Action (shared):** Shifted the existing effect bundle from +10% recoil control / +10% dispersion improvement to +5% recoil control / +15% dispersion improvement. The 10% slower firing cycle remains; High-Cyclic System is unchanged. Updated the shared module catalog to match the generator.
- **SMGs – Stabilized Readiness:** Replaced +15% recoil control and +20% shot recovery with +15% idle-sway stability on both axes; the 10% aiming-time penalty remains. This avoids duplicating Tactical Stock's exact effect bundle.
- **SMGs – Controlled Action (class-specific):** Reduced shot recovery from +20% to +10%; recoil, reload and fire-cycle effects remain unchanged. This is distinct from the shared Controlled Action module.
- **SMGs – Tactical Stock:** Reduced shot-recovery bonus from +20% to +10%; recoil control and aiming-time penalty remain unchanged.
- **SMGs – Stabilized Stock:** Reduced recoil-control bonus from +20% to +15%; dispersion improvement and weight penalty remain unchanged.
- **Pistols – Balanced Action:** Reduced shot recovery from +20% to +10% to limit combined automatic-fire control.
- **Pistols – Controlled Action:** Reduced shot recovery from +20% to +10%; slower firing and recoil control remain.
- **Pistols – Stabilized Handling:** Replaced +20% shot recovery with +15% idle-sway stability on both axes, differentiating steady aiming from action/recoil specialization.
- **Shotguns – Reinforced Action:** Reduced shot recovery from +20% to +10%; recoil control and slower cycling remain.
- **Shotguns – Stabilized Furniture:** Reduced shot recovery from +20% to +10%; recoil, weight and aiming penalties remain.
- Updated affected module descriptions in English, Russian and Simplified Chinese.

### Development notes
- Generator sources and localization definitions have been updated, and the maintainer has regenerated and pushed CFGs. **In-game behavior has not yet been validated.**
- Upgrade UI issues and broader balancing ideas remain outside this changelog until actual changes are implemented.
- 7.62×39 (`A762`) conversions and ammunition behavior remain unchanged.

<!-- Add future implemented changes under Unreleased; move entries into a versioned section when a release is published. -->
