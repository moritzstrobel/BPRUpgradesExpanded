# Pistol specialization design

Normal pistol families use two shared three-way specialization groups plus one standalone family-specific signature module. Unique weapon variants are excluded and will be handled separately.

## Shared groups

### Action
- High-Speed Action: faster cycle, higher recoil and wear.
- Balanced Action: moderately faster cycle and lower recoil, small wear penalty.
- Controlled Action: slower cycle, lower recoil and faster recoil recovery.

### Handling
- Quick-Draw Setup: lighter and faster to aim, with increased recoil.
- Tactical Setup: balanced aiming, aimed movement and recovery improvements.
- Stabilized Setup: lower recoil and faster recovery, but slower aiming.

## Signature modules

### PTM — Quick-Response Package
Emergency-backup role: very fast aiming/reload and low weight, traded for recoil and wear.

### UDP — Match Barrel Assembly
Precision/mid-range sidearm: tighter dispersion, longer effective falloff and higher projectile speed, traded for slower handling.

### APB/APSB — Automatic Sear
APB is natively three-round burst (`EFireType::Queue`, `FireQueueCount = 3`). Uses vanilla `ChangeFireTypeEffectBurstAuto` to expose Queue + Automatic modes.

### Rhino — Hunting Cylinder
Conservative first pass because Rhino already has a vanilla 12-gauge conversion branch. Ammo-specific behavior is deferred until that interaction is mapped.

### M10 Gordon — Selectable Fire Control
M10 is natively automatic. Vanilla `ChangeFireTypeEffectSemiAuto` exposes SemiAutomatic + Automatic.

## Verified baseline
- `GunAPB_HG`: FireInterval 0.085; Queue; FireQueueCount 3.
- `GunM10_HG`: FireInterval 0.045; Automatic.
- `GunPM_HG`: FireInterval 0.09; AimingTime 0.25.
- `GunUDP_HG`: FireInterval 0.08; AimingTime 0.25.
- `GunRhino_HG`: FireInterval 0.7; AimingTime 0.38.
