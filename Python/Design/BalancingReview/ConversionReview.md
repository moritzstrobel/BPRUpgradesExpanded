# Caliber conversion review — implementation plan (2026-10-06)

**Status:** analysis and design proposal only. No conversion generator/effect changes committed yet. Original tester feedback is archived in `balacingBaseOverview.txt`; track dispositions in `TesterFeedbackProgress.md`.

## Observed generator baseline

- Sniper/DMR: `CALIBER_CONVERSIONS` in `Snipers/generate_sniper_upgrades.py` maps `A762Sniper` (7.62×54R) to `A762NATO` (.308) and vice versa. Each direction has Default/AP/Supersonic variants, distinct ammo restriction effects and mutually blocking variants. Seven configured families: SVDM, SVU, Mark, M701, SIC, ThreeLine, GP3A.
- Sniper .308 → 7.62×54R Default: +10% damage, +15% armor piercing, recoil penalty 15%, wear-per-shot penalty 15%. AP: +5% damage, +25% AP, recoil penalty 20%, wear penalty 15%. Supersonic: +10% damage, +10% AP, recoil penalty 15%, wear penalty 15%, +15% flatness. The extra damage/AP bonuses are the primary economy-versus-power concern.
- Sniper 7.62×54R → .308 Default: +10% recoil control, -10% damage; AP: +15% AP, +5% recoil control, -15% damage; Supersonic: +10% recoil control, -10% damage, +15% flatness.
- AR: `POWER_CALIBER` maps `A545` → `A762Sniper`, `A556` → `A762NATO`. AK74 and Gvintar additionally configure `A762` (7.62×39). Fora, Kharod and Dnipro disable BPRUE conversion in favor of vanilla conversion ownership. G37, M16, Arev use 7.62 NATO conversion; Grim and Lavina have no generated conversion under current rules.
- AR default `A762Sniper` conversion has +15% damage/+15% AP, 25% recoil and 20% wear penalties; default `A762NATO` has +10% damage/+15% AP, 20% recoil and 15% wear penalties. Variant-specific stats also exist.
- Vanilla conversion reference matrix: `Python/Analysis/Reports/caliber_conversion_matrix.json`; source analysis: `Python/Analysis/analyze_caliber_conversions.py`, `analyze_conversion_profiles.py`. The report is a repository snapshot, **not** proof of runtime effect ordering or technician behavior.

## Original feedback mapped to decisions

| Tester observation/request | Assessment | Proposed work | Status |
| --- | --- | --- | --- |
| .308 → 7.62×54R can be a no-brainer because of ammunition economy and damage/AP buffs | Plausible from current generator stats | Replace unconditional damage/AP gains with meaningful velocity, flatness and damage-dropoff disadvantages; compare base projectile stats and real economy first | **OPEN** |
| 7.62×54R → .308 lacks an incentive | Current -damage defaults may reinforce complaint | Build a long-range ballistic niche with velocity/flatness/dropoff rather than stacking damage/AP; validate effect behavior | **OPEN** |
| AP/Supersonic-only conversion restrictions bypassed by vanilla Barrel Hardening | Functional bug reported, not reproduced | Identify exact vanilla Barrel Hardening upgrade SIDs, its ammo effects, and application precedence; test install orders both ways and save/reload | **OPEN / high priority** |
| Three variants per target caliber may be unnecessary | Adds overlapping restriction effects and combinatorics | Evaluate a single generic conversion per direction; retain existing SIDs or plan explicit migration/compatibility for existing saves | **OPEN / design decision** |
| AR conversions are overly broad and favor DMR calibers | Supported by AR power-caliber mapping | Audit per-weapon identity, vanilla conversion ownership, unique signatures, attachment/layout constraints and realistic target calibers; do not bulk-add calibers | **OPEN** |
| 7.62×39 is unavailable in base-game economy | Valid external-mod compatibility concern | **Keep `A762` support unchanged** as explicit project policy; no ammo vendor injections | **DECIDED — unchanged, not a fix** |
| Integrated-suppressor families should not receive implausible conversions | Grim/Lavina currently lack BPRUE conversion; Gvintar has `A762` | Keep current state pending weapon identity/compatibility tests; no blanket changes | **REVIEWED** |

## Implementation stages and gates

1. **Technical correctness:** Inspect actual vanilla `Barrel Hardening` upgrade and ammo-effect chain; distinguish changing caliber, adding ammo types, and removing ammo types. Validate installation order and inheritance. Fix bypass with narrow, tested behavior; avoid breaking vanilla upgrades or unique variants.
2. **Per-family conversion matrix:** Record source/target, ammo availability, magazine capacity, vanilla ownership, current BPRUE variant SIDs, exact stats and target gameplay role. Do not assume source report captures all DLC/edition/unique variants.
3. **Sniper ballistic redesign:** Prototype one reversible profile per direction; test effect SID availability and signs, especially `ProjectileSpeed`, `Flatness`, `DistanceDropOffLength`. Decide whether to preserve or consolidate Default/AP/Supersonic variants with a save-compatibility plan.
4. **AR conversion redesign:** Preserve `A762` and vanilla-owned conversions. Review high-powered AR conversions individually rather than mechanically following the tester's proposed weapon list.
5. **Validation:** Generate CFGs, check all effect references and localization (EN/RU/ZH), mutual blocking, attachment/layout, variant save behavior, both vanilla-upgrade installation orders, reload/save and representative gameplay/economy comparisons.

**Do not mark original conversion feedback as addressed until changes are implemented; do not mark it fixed until in-game verification.**
