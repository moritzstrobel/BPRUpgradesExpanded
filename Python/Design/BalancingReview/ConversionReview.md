# Caliber conversion review — implementation plan (2026-10-06)

**Status:** partial implementation. Sniper/DMR and AR conversion profiles changed in generator sources; the maintainer has regenerated and pushed CFGs. The generated AR shared effects have been confirmed present, but full upgrade wiring, effect stacking, ammo behavior and in-game results remain unverified. SMG conversions remain unchanged. Original tester feedback is archived in `balacingBaseOverview.txt`; track dispositions in `TesterFeedbackProgress.md`.

## Observed generator baseline

- Sniper/DMR: `CALIBER_CONVERSIONS` in `Snipers/generate_sniper_upgrades.py` maps `A762Sniper` (7.62×54R) to `A762NATO` (.308) and vice versa. Each direction has Default/AP/Supersonic variants, distinct ammo restriction effects and mutually blocking variants. Seven configured families: SVDM, SVU, Mark, M701, SIC, ThreeLine, GP3A.
- Sniper .308 → 7.62×54R Default (current): −10% projectile speed, −10% flatness, −15% damage drop-off length, 10% recoil penalty and 10% additional wear per shot; no damage/AP modifiers. AP: inherits Default with +5% AP and -5% damage. Supersonic: inherits Default with +5% projectile speed and +5% additional wear per shot. The extra damage/AP bonuses are the primary economy-versus-power concern.
- Sniper 7.62×54R → .308 Default (current): +10% projectile speed, +10% flatness, +15% damage drop-off length and +5% recoil control, no damage penalty; AP: inherits Default with +5% AP and -5% damage; Supersonic: inherits Default with +5% projectile speed and +5% additional wear per shot.
- AR: `POWER_CALIBER` maps `A545` → `A762Sniper`, `A556` → `A762NATO`. AK74 and Gvintar additionally configure `A762` (7.62×39). Fora, Kharod and Dnipro disable BPRUE conversion in favor of vanilla conversion ownership. G37, M16, Arev use 7.62 NATO conversion; Grim and Lavina have no generated conversion under current rules.
- AR `A545` → `A762Sniper`: +5% damage, −5% flatness, +5% damage drop-off length, 25% recoil penalty and +20% wear per shot. `A556` → `A762NATO`: +5% damage, +5% flatness, +10% damage drop-off length, 20% recoil penalty and +15% wear. All AP/Supersonic variants inherit the full baseline and add +5% AP or +5% projectile speed, respectively. No unconditional AP boost in Default.
- AR `A545` → `A762` (7.62×39): +5% damage, −10% flatness, −10% damage drop-off length, 15% recoil penalty, +10% wear. `A939` → `A762` (VS Vintar) instead uses +5% projectile speed, +5% damage drop-off length, 15% recoil penalty and +10% wear. AP adds +5% armor penetration; Expanding relies on ammunition-specific modifiers. 7.62×39 remains intentionally supported despite reported vanilla ammo unavailability.
- Vanilla conversion reference matrix: `Python/Analysis/Reports/caliber_conversion_matrix.json`; source analysis: `Python/Analysis/analyze_caliber_conversions.py`, `analyze_conversion_profiles.py`. The report is a repository snapshot, **not** proof of runtime effect ordering or technician behavior.

## Original feedback mapped to decisions

| Tester observation/request | Assessment | Proposed work | Status |
| --- | --- | --- | --- |
| .308 → 7.62×54R can be a no-brainer because of ammunition economy and damage/AP buffs | Plausible from current generator stats | Replace unconditional damage/AP gains with meaningful velocity, flatness and damage-dropoff disadvantages; compare base projectile stats and real economy first | **PARTIAL — generated, unverified** |
| 7.62×54R → .308 lacks an incentive | Current -damage defaults may reinforce complaint | Build a long-range ballistic niche with velocity/flatness/dropoff rather than stacking damage/AP; validate effect behavior | **PARTIAL — Default only** |
| AP/Supersonic-only conversion restrictions bypassed by vanilla Barrel Hardening | Functional bug reported, not reproduced | Identify exact vanilla Barrel Hardening upgrade SIDs, its ammo effects, and application precedence; test install orders both ways and save/reload | **OPEN / high priority** |
| Three variants per target caliber may be unnecessary | Adds overlapping restriction effects and combinatorics | Evaluate a single generic conversion per direction; retain existing SIDs or plan explicit migration/compatibility for existing saves | **OPEN / design decision** |
| AR conversions are overly broad and favor DMR calibers | Existing target-caliber matrix retained as project choice, despite tester's AR-native-caliber recommendations | Reduced unconditional damage/AP buffs, added trajectory/drop-off/recoil/wear trade-offs and separate VS Vintar profile; test whether ammunition economy still makes any conversion a no-brainer | **PARTIAL — generated, unverified; matrix not adopted** |
| 7.62×39 is unavailable in base-game economy | Valid external-mod compatibility concern | **Keep `A762` support unchanged** as explicit project policy; no ammo vendor injections | **DECIDED — unchanged, not a fix** |
| Integrated-suppressor families should not receive implausible conversions | Grim/Lavina currently lack BPRUE conversion; Gvintar has `A762` | Keep current state pending weapon identity/compatibility tests; no blanket changes | **REVIEWED** |

## Implementation stages and gates

1. **Deferred technical correctness:** Inspect actual vanilla `Barrel Hardening` upgrade and ammo-effect chain; distinguish changing caliber, adding ammo types, and removing ammo types. Validate installation order and inheritance. Fix bypass with narrow, tested behavior; avoid breaking vanilla upgrades or unique variants.
2. **Per-family conversion matrix:** Record source/target, ammo availability, magazine capacity, vanilla ownership, current BPRUE variant SIDs, exact stats and target gameplay role. Do not assume source report captures all DLC/edition/unique variants.
3. **Sniper ballistic redesign:** Preserve all Default/AP/Supersonic variants as mutually exclusive complete profiles. The directional baselines are implemented; verify effect signs, stacking and runtime behavior after testing.
4. **AR conversion redesign:** Existing target-caliber matrix, `A762` support and vanilla-owned conversions preserved. Source profiles rebalanced and CFGs regenerated. Validate the per-weapon gameplay role and ammo economy rather than assuming tester-recommended alternative calibers.
5. **Validation:** Generate CFGs, check all effect references and localization (EN/RU/ZH), mutual blocking, attachment/layout, variant save behavior, both vanilla-upgrade installation orders, reload/save and representative gameplay/economy comparisons.

**Sniper/DMR and AR conversion generator changes have been regenerated and pushed, but in-game validation remains outstanding. Multiple same-type effects and any `KeepAll`-style setting require a later global effect test. Barrel Hardening bypass remains deferred; do not mark tester feedback fully fixed.**
