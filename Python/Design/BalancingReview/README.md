# BPRUE – Balancing & Upgrade Design Review

> **Status:** Design proposal / investigation backlog — **not approved for implementation**  
> **Base:** `develop` (2026-10-06, `e0f22937`)  
> **Scope:** Weapons, specializations, caliber conversions, upgrade-tree UI, repair economics  
> **Input:** External playtest feedback (`balacingBaseOverview.txt`). This document is a **BPRUE-specific interpretation**, not a copy or automatic acceptance of the review.

## 1. Principles and non-goals

BPRUE exists to expand meaningful upgrade choices and extend progression. Strong modules are acceptable, but *unconditional upgrades that dominate every alternative* undermine specialization. Balance must be judged **per weapon and in combination with vanilla upgrades and other BPRUE groups**, not merely by individual effect percentages.

- Keep meaningful trade-offs and multiple viable builds; do not flatten all weapons into identical balance profiles.
- Preserve weapon identity, vanilla progression, unique weapons and existing upgrades unless there is a demonstrated reason to change them.
- Prefer numerical tuning and role clarification before deleting entire upgrade/module families.
- Separate **technical defects**, **confirmed balance concerns**, **design proposals** and **unverified player preferences**.
- **No blanket removal of armor-penetration modules or caliber conversions.**
- **7.62×39 (`A762`) must stay.** Lack of widespread vanilla ammunition supply is **not a BPRUE bug or action item**: players may deliberately use mods reintroducing or distributing this ammunition. BPRUE does not promise to stock merchants, spawn ammunition on NPCs or validate every optional cross-mod combination. Do not silently substitute a different caliber or remove the conversion.
- Do not change generated CFGs directly. Design adjustments belong in JSON catalogs or Python generators, followed by regeneration and audit.
- Avoid speculative numerical targets presented as final values. Confirm game-engine effect semantics before adjusting signs, percentages or effect identifiers.

## 2. Repository implementation map

| Responsibility | Source of truth / relevant code | Notes |
|---|---|---|
| Global/shared module identities and intended stat deltas | `Python/CFGGenerators/Common/specialization_module_catalog.json` | Shared handling, recoil/precision, action, ballistics, reliability, range |
| Shared module **actual effect SIDs** and membership | `Python/CFGGenerators/Common/specialization_modules.py` | `MODULE_EFFECTS` drives generated upgrades; `GROUP_META` assigns groups/sections |
| Shared class registrations | `Python/CFGGenerators/Common/shared_upgrades.py` | Uses weapon-class families/configs |
| AR family selection and native AR module balance | `Python/CFGGenerators/AssaultRifles/assault_rifles_upgrades.json`; `generate_assault_rifle_upgrades.py` | `MODULE_SPECS`, `POWER_CALIBER`, `CALIBER_EFFECTS`, variant tables, `_EFFECTS` |
| DMR/sniper families, variants and effects | `Python/CFGGenerators/Snipers/sniper_upgrades.json`; `generate_sniper_upgrades.py` | `BALLISTICS`, `ACTION`, `MARKSMAN`, `STOCK`, `CALIBER_CONVERSIONS` |
| Group allocation and fallback sections | `Python/CFGGenerators/Common/apply_module_layout.py`; `vanilla_upgrade_layout.py` | Visible-column budget and fallback target selection |
| Rendered upgrade, setup and technician CFGs | `Python/CFGGenerators/Common/upgrade_renderers.py`; `Python/generate_all_cfg.py` | Generated output, not primary edit point |
| Gameplay effects and vanilla baselines | `Python/VanillaReference/EffectPrototypes.cfg`, weapon/general-setup/upgrade prototypes | Check inheritance and engine semantics |
| Conversions and ammo diagnostics | `Python/Analysis/analyze_caliber_conversions.py`; `analyze_conversion_profiles.py` | Analyze actual configurations, not a proposed ammo-availability gate |
| Upgrade placement / UI diagnostics | `Python/Analysis/analyze_weapon_upgrade_sections.py`; `build_vanilla_upgrade_map.py`; `build_bprue_upgrade_map.py`; `analyze_upgrade_layouts.py` | Existing report pipeline |
| DLC / Edition / compatibility | `Python/CFGGenerators/Common/dlc_weapon_modules.py`, `edition_weapon_modules.py`; `Python/OXA/`; `Compat/OXA/` | Audit coverage whenever shared definitions change |
| Localization | `Python/Localization/`; `Localization/` | Descriptions must match real effect trade-offs |

The JSON catalog contains human-readable `effects` metadata, but **`MODULE_EFFECTS` in `specialization_modules.py` is what the current generator actually assigns**. Keep these representations in sync. In particular, a catalog stat named `effective_fire_distance` does not by itself establish actual projectile trajectory behavior.

## 3. Triage and decisions

| ID | Feedback / observation | Classification | Decision |
|---|---|---|---|
| UI-01 | Long module lists clip or approach screen boundaries | Reported defect | **Investigate / reproduce** |
| UI-02 | Pistol upgrade nodes may float near disabled/unused attachment sections | Reported defect | **Investigate / reproduce** |
| AP-01 | Armor-penetration/soft-target specialization can have disproportionate results across tiers | Balance concern | **Measure; retain pending evidence** |
| ECO-01 | Late-upgraded low-tier weapons may have overly cheap repairs | Economy concern | **Measure total repair cost before tuning** |
| AMMO-01 | 7.62×39 ammunition not broadly supplied | Optional compatibility/economy choice | **Out of scope, no change** |
| CAL-01 | Sniper ammo-restriction conversion bypassed by vanilla Barrel Hardening | Reported interaction defect | **Reproduce & isolate** |
| CLASS-01 | VS Vintar classified as AR, although a DMR role is suggested | Design suggestion | **Review intentional identity, no automatic move** |
| DMR-01 | Multiple recoil and stability improvements stack into highly effective close-range DMRs | Balance concern | **Measure combined builds** |
| DMR-02 | Some precision stock, marksman, heavy barrel, benchrest and similar choices dominate | Balance concern | **Review per module** |
| DMR-03 | .308 / 7.62×54R conversions and variant-specific ammo restrictions feel too rewarding or awkward | Design proposal | **Evaluate per caliber and ammo rule** |
| AR-01 | ARs can become extremely accurate automatic weapons without sufficient opportunity cost | Balance concern | **Measure and redesign trade-offs if confirmed** |
| AR-02 | Precision/Burst Fire Control and competing stock/action modules may lack differentiated roles | Design proposal | **Compare alternatives and actual fire-mode semantics** |
| AR-03 | Restrict all AR caliber changes to other AR calibers | Design proposal | **Do not adopt as a blanket rule** |
| COST-01 | Existing repair cost modifier `RepairCostModifier = 0.2` reportedly cheap | Unverified systemic detail | **Trace inheritance/formula and game economy first** |

**Evidence labels** in this document: *Confirmed in repository* = definition/code exists; *Reported* = tester observation not yet reproduced; *Proposal* = optional direction; *Decision* = scoped policy for this review.

## 4. Upgrade-tree UI

### UI-01: clipped module columns / labels
The tester proposes switching `ModuleLineDirection = ELineDirection::Right` to `Left`. Do **not** globally flip it: direction varies already in vanilla sections, and node placement depends on section position, rendered column count, group allocation and available screen space.

**Inspect:**
- `Python/CFGGenerators/Common/apply_module_layout.py`: `GROUP_ORDER`, `_target_order()`, `_first_free_column()`, `_standalone_cell()`, `VERTICALS`.
- `Python/CFGGenerators/Common/vanilla_upgrade_layout.py`: `MAX_VISIBLE_HORIZONTAL_POSITION = 2`, `free_visible_columns()`, section inheritance.
- `Python/Analysis/analyze_weapon_upgrade_sections.py`: `ModuleLineDirection`, `UpgradeLineDirection`, target part positions.
- `Python/VanillaReference/WeaponPrototypes.cfg` and DLC equivalents for ground truth.

**Investigation plan:** capture exact weapon SIDs, resolution, screenshots and overflowing group(s); produce an occupancy/section direction report; test per-weapon patching only on affected sections. Preserve UI on normal weapons and DLC/uniques.

### UI-02: floating pistol sections
`apply_module_layout._target_order()` presently calls `available_target_parts(..., include_disabled=True)`. This can make fallback sections available for layout even if vanilla marks them disabled. That fact alone does **not** prove which patch causes a visibly floating node; it provides an actionable hypothesis.

**Plan:** build a pistol matrix of enabled/disabled sections, assigned groups and per-section capacity. Prefer enabled vanilla attachment points when they fit; otherwise explicitly justify a section override or a class-specific layout. Check regression for upgrades, prerequisites, 3 vertical slots and H0–H2 visibility. Do not globally set `include_disabled=False` before checking allocation capacity.

## 5. Shared specialization balance

**Source files:** `specialization_module_catalog.json`, `specialization_modules.py`, `shared_effects.py`, localization texts.

### AP-01: Soft-Target versus Armor-Piercing
Current *effective* shared bundles in `MODULE_EFFECTS`:
- `soft_target`: `DamagePos15Effect`, `FlatnessUp10Effect`, `ProjectileSpeedPos10Effect`, `BPRUE_Shared_ArmorPiercingPenalty20Effect`.
- `armor_piercing`: `ArmorPiercingPos25Effect`, `CoverPiercingPos20Effect`, `BPRUE_Shared_DamagePenalty10Effect`.

These represent deliberate trade-offs, not obviously unconditional upgrades. Tester requests **removing both** to avoid tier-sensitive armor penetration; **not accepted by default**.

**Before decisions:** evaluate identical targets at multiple armor levels, weapon tiers and ammo variants; compare damage-to-kill with/without AP against other modules and stackable vanilla effects. Preserve a real lightly-armored versus armored target specialization if feasible. Validate that tooltips communicate AP penalties correctly. If scaling is severe, tune magnitudes or gate by class rather than delete wholesale.

### Shared recoil / precision / action
- `recoil_control`: `RecoilPos15Effect` with `BPRUE_Shared_DispersionPenalty5Effect`.
- `precision_tuning`: `DispersionPos15Effect` with `BPRUE_Shared_RecoilPenalty8Effect`.
- `high_cyclic_system` vs `controlled_action` must be compared with **AR-native** `HighSpeed`/`Balanced` and sniper action groups, not evaluated in isolation.

Suggested experiment: compute recoil, sway, dispersion, fire rate and handling for default / best-case stacked / role-specialized builds. Record whether penalties are still noticeable after stacking. For `precision_tuning`, the tester suggests flatness or damage drop-off; evaluate actual `EffectiveFireDistance` and `DistanceDropOffLength` behavior before replacing dispersion.

### Economy
The report claims a module/upgrade `RepairCostModifier = 0.2` and estimates a simple purchase-price fraction. Do not treat that alone as proof of final repair-cost calculation: check upgrade template inheritance, stacking, actual repair quote on several tiers and durability levels, then tune only if upgraded entry-level guns gain an unintended economic advantage. Consider price and wear together; avoid making all early-game modules punitive.

## 6. DMR / sniper redesign candidates

**Actual source:** `Python/CFGGenerators/Snipers/sniper_upgrades.json` (`families`, `module_groups`); `generate_sniper_upgrades.py` (`BALLISTICS`, `ACTION`, `MARKSMAN`, `STOCK`, `CALIBER_CONVERSIONS`, `render_effects`).

**Current families:** `SVDM`, `SVU`, `Mark`, `M701`, `SIC`, `ThreeLine`, `GP3A`. `Gvintar`/VS Vintar is currently in the AR family registry. Moving it would also affect shared-class groups, setup registrations, layouts, unique variants, DLC/edition matching and compatibility. **No migration without an explicit per-weapon design decision.**

### Test proposed identities
- **Precision/long range**: projectile velocity, supported range/flatness, controllability between shots, aimed stability. Costs: mass, aiming speed, readiness and/or rate of fire.
- **Mobile/mid range**: handling, movement while aiming, faster target acquisition. Costs: recovery after repeated shots, long-distance performance and/or wear.
- Avoid universally stacking hip-fire, sustained automatic recoil control and long-range accuracy to beat ARs at both roles.

### Module-specific review
| Module | Current source behavior (effect SIDs or roles) | Proposed investigation (not committed change) |
|---|---|---|
| Lightweight Stock | Aim time + movement, recoil penalty | Keep as baseline |
| Adjustable Stock | Idle sway X/Y + movement + recoil | Reported near-free combination; reduce one benefit or add meaningful cost if dominance confirmed |
| Precision Stock | Strong idle sway X/Y + recoil + shot recovery, aim-time penalty | Check **sway X/Y are distinct axes**, not automatically duplicate stacking; assess replacing raw recoil buff |
| Hardened / Lightweight Components | Shared reliability opposite trade-offs | Keep unless economy or weight tests reveal issues |
| Range Configuration | Flatness + dispersion, slower aiming | Test actual differentiation before deletion |
| CQB Configuration | Faster aim + dispersion + shorter effective range | Potential shot-recovery trade-off, check per weapon |
| Benchrest | Large sway X/Y + recoil, weight/aim-time costs | Reduce stacked control; consider shot-recovery instead of raw recoil |
| Snapshooter | Aim time + aiming movement, recoil penalty | Keep as baseline |
| Field Marksman | Aiming movement + sway X/Y + shot recovery, no obvious direct cost | High-priority dominance test; add downside or reduce benefits |
| Recoil Control / Precision Tuning | Shared control vs dispersion trade-offs | Test stacked effects; precision semantics first |
| High-Velocity Ballistics | Speed + drop-off, recoil/wear costs | Keep concept |
| Match Barrel | Dispersion + range, aiming-time cost | Test long-range impact, optional wear penalty |
| Heavy Barrel | Recoil + recovery, weight/aim-time costs | Evaluate readiness versus additional recoil improvement |
| Rapid / Precision / Reinforced Action | Fire cycle vs stability/durability trade-offs | Review across bolt-action, semi-auto and automatic DMR variants |

The user feedback's `OP` labels are hypotheses, not measured proof. Do not conflate `IdleSwayX` + `IdleSwayY` with an accidental duplicate when they may intentionally represent two axes.

## 7. Sniper conversion and ammo-restriction compatibility

**Current implementation:** `CALIBER_CONVERSIONS` has **Default, AP, Supersonic** variants for `A762Sniper` → `A762NATO` and vice versa. The variants intentionally combine caliber, allowed ammo types and extra stat effects.

**CAL-01: vanilla Barrel Hardening** — tester reports SVD/SVU/ThreeLine/M701 conversions can acquire more ammunition types than an AP-/Supersonic-restricted variant allows after installing the vanilla upgrade.

**Do not remove the conversions by default.**
1. Identify exact vanilla Barrel Hardening upgrade SIDs and `EffectPrototypeSIDs` from `Python/VanillaReference/`.
2. Reproduce installing the upgrades in **both orders** on each affected weapon; inspect allowed ammo types after swapping and reloading.
3. Trace whether `ChangeAmmoTypes` effects replace, merge or override a weapon's ammo-type list and which upgrade executes last.
4. Candidate fixes: explicit incompatibility rules *if* vanilla/BPRUE blocker references work across both upgrade sets; remove only restrictive ammo-variant behavior while keeping generic conversion; or re-author ammo-type effects. Do not add blind blocks to `blocking_sids` without validating `UpgradeBuildModel.validate()` (requires generated SIDs) and renderer semantics.
5. Check unique weapons, DLC, OXA, and any pre-installed Barrel Hardening save migration effects.

**CAL balance:** tester argues .308 ammo rarity and 7.62×54R abundance should drive trade-offs. That is one design input, not a mandatory realism or availability rule. Measure actual damage/AP/velocity/drop-off from each generated effect chain; some `A762NATO`→`A762Sniper` variants currently give positive damage/AP and substantial recoil/wear penalties. The proposed *velocity/flatness instead of raw damage/AP* trade may be promising, but do not replace all three variants automatically. First determine whether their ammo restrictions are both technically consistent and interesting.

**Do not confuse `A762` (7.62×39) with `A762Sniper` (7.62×54R).** There is **no work item** to remove `A762` conversions or supply its ammunition via traders.

## 8. Assault-rifle redesign candidates

**Actual source:** `Python/CFGGenerators/AssaultRifles/assault_rifles_upgrades.json`; `generate_assault_rifle_upgrades.py` (`MODULE_SPECS`, `CALIBER_EFFECTS`, `POWER_CALIBER`, `A762_CONVERSION_VARIANTS`, etc.); shared catalog and `specialization_modules.py`.

**Current AR families:** `AK74`, `Fora`, `G37`, `M16`, `Kharod`, `Arev`, `Dnipro`, `Gvintar`, `Grim`, `Lavina`. Current data intentionally disables BPRUE conversions where `bprue_caliber_conversion=false` (Fora, Kharod, Dnipro). `AK74` and `Gvintar` have additional `A762` variants. Tester-proposed specific weapons/calibers do **not** map directly to current configs; do not mechanically copy their list.

### Suggested role distinction
- **Assault/mobile:** readiness, manageable short-range dispersion and ADS movement; penalties on repeated-shot precision at range, recoil, effective range or wear.
- **Controlled/medium-long:** recovery between bursts, aimed stability/accuracy, modest recoil; penalties on aim time, movement speed, weight and/or cyclic rate.
- Retain meaningful automatic-fire control even if semi-auto and burst are options; avoid building a universally better AR.

### Concrete source review
| AR module | Current effective module spec | Decision / experiment |
|---|---|---|
| Precision Fire Control | `BPRUE_SemiAutoOnlyEffect`, damage +10%, AP +15%, wear cost | **Review**, not remove: test whether lost full-auto is a meaningful opportunity cost; consider unique-weapon identity |
| Burst Fire Control | `BPRUE_AddBurstFireModeEffect`, recoil benefit, wear cost | Proposed *replace full-auto with burst* requires a **different** fire-mode effect/semantics; cannot be achieved by description change |
| High-Speed Operation | Fire interval -20%, recoil/wear penalties | Test stacked DPS/control and role |
| Balanced fire-rate | Fire interval -10%, recoil +10%, shot recovery +20%, wear cost | Compare to shared controlled/high-cyclic action choices |
| Competition Reload | Reload time -20%, recoil malus | Optional recoil → dispersion trade: test identity and stacking |
| Reinforced Reload | Reload time -10%, durability-per-shot benefit, fire interval penalty | Tester suggests removing reload advantage; decide based on actual feed/reliability role |
| Lightweight Stock | Faster aim/movement, recoil cost | Keep candidate |
| Stabilized Stock | Recoil +15%, recovery +20%, aim-time cost | Measure dominance; **no automatic deletion** |
| Marksman Stock | Sway X/Y +20%, dispersion +15%, aim-time cost | Confirm which effects apply while aiming and their relative power |
| Tuned Gas / High-Cyclic / Controlled Action | Shared vs AR-native action effects | Check redundancy and whether names/effects encode distinct trade-offs |
| Recoil Control / Precision Tuning | Shared recoil/precision group | Check aggregate recoil/dispersion and actual accuracy semantics |

The tester also proposes 5.45, 5.56 and 9mm conversions for specific ARs. Do **not** blanket-convert every weapon to arbitrary caliber pairs; check vanilla conversion ownership, unique variants, weapon identity, ammo-type rules, projectile behavior, UI grouping and blocking semantics per family. Retain intentional `A762` support regardless of vanilla ammunition economy.

## 9. Acceptance and measurement plan

### Required baseline
Capture unmodified vanilla, current BPRUE, and proposed BPRUE results for representative **Tier 1 / mid-tier / endgame** weapons. Within each class record:
- time to kill versus **unarmored**, **medium armor**, **heavy armor**, and at least one mutant;
- recoil, time-to-reacquire, burst dispersion / ADS accuracy, sway, sustained fire;
- effective damage at short/medium/long range; separate projectile velocity, trajectory and damage drop-off where testable;
- movement/aim time, readiness, reload speed, durability use and repair cost;
- ammo compatibility before/after vanilla upgrades, save reload and technician changes;
- tree readability at multiple display resolutions, all affected pistol sections.

### Suggested analysis improvements (separate implementation tasks)
- Aggregate **all attainable module stacks** by weapon family, including vanilla modifications; report min/max key stats and trade-off penalties.
- Report dominated mutually exclusive options (same or worse trade-off for all measured stats), ignoring costs only when deliberately testing combat trade-offs.
- Detect unavailable or clipped target sections per weapon and content pack; collect `ModuleLineDirection` along with actual allocated upgrade groups.
- Reproduce `Barrel Hardening` conflict with effect ordering and ammo-type lists.
- Cross-check shared catalog `effects` metadata against `MODULE_EFFECTS` SIDs and effect definitions.
- Validate production of all base-game, DLC, Edition and OXA outputs with existing audit scripts.

### Validation and rollout
1. **No gameplay changes in this design branch**; amend design decisions first.
2. For later implementation branches, modify source generator/catalog, not derived CFG.
3. Regenerate with `Python/generate_all_cfg.py` and run applicable `Python/Analysis/` audits according to their CLI/readme.
4. Verify module mutual exclusion, UI slots, name/description localization, technician availability, DLC/Edition/OXA compatibility.
5. Smoke test in game, including old saves and vanilla upgrade order, before accepting balance changes.

## 10. Decision backlog

| Order | Item | Next decision / evidence needed | State |
|---|---|---|---|
| P0 | UI clipping & floating pistol nodes | Weapon SID screenshots + layout diagnostics | Investigation |
| P0 | Sniper Barrel Hardening bypass | Upgrade SID, effect order and ammo outcome repro | Investigation |
| P1 | AR/DMR extreme recoil-control stacks | Per-class combined build stats and test clips | Investigation |
| P1 | Field Marksman / adjustable or precision stocks / benchrest | Identify dominated variants and quantify alternatives | Investigation |
| P1 | Armor Penetration tier sensitivity | Damage-to-kill measurements before any nerf | Investigation |
| P2 | Alternative AR and DMR specialization identities | Agree role targets, then adjust generators | Proposal |
| P2 | Economy / repair modifiers | Measure quotes; establish real modifier inheritance | Investigation |
| P2 | Sniper caliber role and ammo variants | Test current restrictions and propose smaller redesign | Proposal |
| **No action** | **7.62×39 distribution or removal** | **Intentionally retained; third-party ammo provisioning is optional** | **Explicitly out of scope** |

---

### Scope note

The external review is valuable test feedback, not the project design authority. In particular, this document does **not** commit to removing unpopular modules, reclassifying VS Vintar, supplying 7.62×39 ammunition, nerfing everything flagged “OP”, or replacing all caliber conversions. Each behavioral change needs a verified current baseline, an intended gameplay role, and regression coverage.
