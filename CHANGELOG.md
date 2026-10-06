# Changelog

Notable changes to BPR Upgrades Expanded are recorded here, independently of design proposals and investigation notes.

This file tracks **implemented changes**, not planned features. Entries under **Unreleased** describe source changes on the current development branch; they are **not yet part of a published release**. Generated game CFGs and in-game validation may still be pending.

## [Unreleased]

### Changed
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
- Updated affected module descriptions in English, Russian and Simplified Chinese.

### Development notes
- Changes above currently affect generator sources and localization definitions. **Generated CFGs have not yet been updated or tested in-game.**
- Upgrade UI issues and broader balancing ideas remain outside this changelog until actual changes are implemented.
- 7.62×39 (`A762`) conversions and ammunition behavior remain unchanged.

<!-- Add future implemented changes under Unreleased; move entries into a versioned section when a release is published. -->
