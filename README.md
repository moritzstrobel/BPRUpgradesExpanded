# BPR Upgrades Expanded

Experimental companion mod for **Blueprint Progression Redone**.

The first test target is the AK-74. The generator creates two additional upgrade prototypes that reuse existing vanilla effect prototypes:

- **+10% fire rate** via `FireRateUp10Effect`
- **-25% reload time** via `ReloadingTimeDecBy25`

This repository intentionally keeps the generated CFG separate from the source JSON and Python generator so upgrade definitions can be iterated quickly.

## Generate CFG

From `Content/Python`:

```powershell
python generate_all_cfg.py
```

Generated output:

```text
Content/GameLite/GameData/UpgradePrototypes/UpgradePrototypes_patch_BPRUE.cfg
```

## Current status

This is an experimental proof of concept. The two AK-74 upgrade prototypes are generated, but the exact integration point into the technician upgrade tree still needs to be verified in-game. The generator therefore keeps the additions isolated and easy to adjust.
