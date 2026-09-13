# BPR Upgrades Expanded

Experimental companion mod for **Blueprint Progression Redone**.

The first test target is the **AKM-74S** (`GunAK74_ST`). The generator creates two additional upgrade prototypes that reuse existing vanilla effect prototypes:

- **+10% fire rate** via `FireRateUp10Effect`
- **-25% reload time** via `ReloadingTimeDecBy25`

The generator also patches `GunAK74_ST.UpgradePrototypeSIDs` so the two new prototypes are actually registered on the weapon.

The vanilla AKM-74S currently occupies upgrade-list indices `0-9`, therefore BPRUE adds its prototypes at `10` and `11`.

## Generate CFG

From `Content/Python`:

```powershell
python generate_all_cfg.py
```

Generated output:

```text
Content/GameLite/GameData/UpgradePrototypes/UpgradePrototypes_patch_BPRUE.cfg
Content/GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg
```

The generated files follow the same prototype-folder patch layout used by Blueprint Progression Redone: the patch file is placed in a folder matching the vanilla prototype file name while preserving the vanilla parent path.

## Current status

This is an experimental proof of concept. The two new UpgradePrototypes are now both defined and registered on `GunAK74_ST`.

The next test is in-game/Zone Kit validation of technician-tree placement, purchase behavior, persistence and the actual gameplay effects. Texts and icons still reuse vanilla AKM-74S entries as placeholders.
