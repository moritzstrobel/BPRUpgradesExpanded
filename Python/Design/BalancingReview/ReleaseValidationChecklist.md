# Release validation checklist — balance pass

**Scope:** QA and release readiness only. Balance decisions are closed in [TesterFeedbackProgress.md](TesterFeedbackProgress.md). Check items off only after actual verification; source-level implementation is not proof of in-game behavior.

## Generated output and packaging
- [ ] Verify all BaseGame, DLC1 and Edition CFG outputs match the latest generator sources, including the repaired `BPRUE_Shared_DropOffLengthPos5Effect` references.
- [x] Localization asset rebuilt with 529 entries and verified with no missing/mismatched values (ZoneKit output reported by maintainer).
- [x] Localization validator reported no remaining errors (maintainer confirmation).
- [ ] Verify packaged/cooked mod uses current CFGs, localization and Vanilla UI patches without merge/load errors.

## Upgrade UI and behavior
- [ ] Verify Barrel/Handguard hotspot orientation and that long module lists remain selectable across representative weapons, DLC and conversion variants.
- [ ] Confirm accepted pistol attachment-point visuals do not interfere with selection or functionality (no visual redesign planned).
- [ ] Verify mutually exclusive modules, UI descriptions and upgrades across weapon classes and tiers.
- [ ] Test repeated Vanilla/BPRUE effect combinations (recoil, flatness, shot recovery and wear). `KeepAll` is inherited from Vanilla `[0]`, but effective stacking still needs gameplay confirmation.
- [ ] Check Soft-Target bleeding-chance behavior against baseline and ammunition effects (relative vs. additive vs. absolute); verify Barrier Module's cover/damage trade-off.
- [ ] Verify standard-module `RepairCostModifier = 0.35` and caliber-conversion `0.25` affect actual repair costs as expected.

## Weapon-specific regression
- [ ] Verify SVD, SVU, Three-Line and M701 conversion variants block Vanilla Barrel Hardening in **both** installation orders, including existing Vanilla blockers, ammunition restrictions and save/reload.
- [ ] Test VS Vintar Sniper/DMR module family and Merc unique; AS Lavina remains AR. Check existing saves with formerly installed Vintar AR modules (known breaking change).
- [ ] Verify AR fire-mode changes (Semi/Burst, Precision), FireRate/Action exclusivity and AR Precision Tuning's flatness/drop-off trade-off.
- [ ] Verify Sniper/DMR module and caliber-conversion ballistics (Default/AP/Supersonic), including actual ammo access and wear/recoil trade-offs.
- [ ] Verify SMG M10, Bucket and Zubr Default/AP/Expanding conversions and ammo-type restrictions.
- [ ] Spot-check other adjusted stock, barrel, action, reload and shotgun/pistol module combinations for unintended dominant choices or regressions.

## Release decision
- [ ] Record test results and any confirmed defects separately; reopen balance values only for reproducible gameplay issues.
- [ ] Check compatibility with representative existing saves and finish cook/install smoke test.
- [ ] Approve release candidate after blockers are resolved.

## Accepted limitations
- Pistol attachment-point visuals are intentionally retained.
- `7.62×39` conversions remain available for mod compatibility; the mod does not add missing ammunition to Vanilla merchants.
