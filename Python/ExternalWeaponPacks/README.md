# External Weapon Pack Compatibility

Personal-use compatibility layer for third-party weapon packs.

The original mod data is **not tracked**. Source CFGs stay below the gitignored
`Python/VanillaReference/MK17Data` and `Python/VanillaReference/ModernAKData`
directories.

## Workflow

```powershell
python Python/ExternalWeaponPacks/Analysis/analyze_weapon_packs.py
python Python/ExternalWeaponPacks/CFGGenerators/generate_weapon_pack_compat.py
```

The analyzer validates/inventories the local source packs. The generator creates
BPRUE-only compatibility files below `Compat/WeaponPacks/GameLite/<Pack>/...`.

All registered weapons are explicitly classified as Assault Rifles. The generator
reuses the normal BPRUE Assault Rifle module definitions and appends them to each
pack's own GeneralSetup. Existing pack upgrades remain untouched.

OXA interaction is deliberately a separate follow-up layer.
