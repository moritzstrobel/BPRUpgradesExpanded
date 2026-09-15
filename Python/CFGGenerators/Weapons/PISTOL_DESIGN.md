# Pistol specialization design

Normal pistol families will eventually use shared specialization groups plus one standalone family-specific signature module. This PR now implements the signature-module phase first. Unique weapon variants remain excluded and will be handled separately.

## Implemented signature modules

### PTM — Quick-Response Package
Emergency-backup role: +20% aiming speed, +20% reload speed and -15% weight, traded for +15% recoil and +10% wear per shot.

### UDP — Match Barrel Assembly
Precision/mid-range sidearm: +30% dispersion improvement, +20% effective falloff distance and +20% projectile speed, traded for 10% slower aiming.

### APB/APSB — Automatic Sear
APB is natively three-round burst (`EFireType::Queue`, `FireQueueCount = 3`). Uses vanilla `ChangeFireTypeEffectBurstAuto` to expose Queue + Automatic modes, traded for +15% recoil and +20% wear per shot.

### Rhino — Hunting Cylinder
Heavy-hunter role: +20% armor penetration and +20% projectile speed, traded for a 10% slower firing cycle. This deliberately does not touch the Rhino's existing vanilla 12-gauge conversion path.

### M10 Gordon — Selectable Fire Control
M10 is natively automatic. Vanilla `ChangeFireTypeEffectSemiAuto` exposes SemiAutomatic + Automatic, with a small recoil-control benefit.

## Verified baseline
- `GunAPB_HG`: FireInterval 0.085; Queue; FireQueueCount 3.
- `GunM10_HG`: FireInterval 0.045; Automatic.
- `GunPM_HG`: FireInterval 0.09; AimingTime 0.25.
- `GunUDP_HG`: FireInterval 0.08; AimingTime 0.25.
- `GunRhino_HG`: FireInterval 0.7; AimingTime 0.38.

## Next pistol phase
The shared pistol specialization groups are intentionally not generated yet. They can be designed around the remaining two active upgrade nodes after the five signatures have been runtime-tested.
