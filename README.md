# BPR Upgrades Expanded

**BPR Upgrades Expanded (BPRUE)** extends the STALKER 2 weapon-upgrade system with additional upgrade modules, weapon-class support, unique/DLC handling and supporting compatibility patches.

> This repository is checked out directly into the Zone Kit plugin's `Content` directory. Paths therefore start at the plugin Content root and must **not** contain another leading `Content/` folder.

## Repository layout

The important distinction is between **source/configuration** and **generated game data**:

| Path | Purpose |
| --- | --- |
| `Python/CFGGenerators/` | Upgrade definitions, per-weapon-class JSON configuration and generator code |
| `Python/Config/` | Configuration used by additional generators |
| `Python/Localization/` | Localization source data and validation tooling |
| `Python/Analysis/` | Analysis/audit scripts and generated reports |
| `Python/VanillaReference/` | Extracted/reference vanilla data used by generators and analysis |
| `GameLite/GameData/` | Generated patches for BaseGame data |
| `GameLite/DLCGameData/` | Generated patches scoped to DLC content |
| `GameLite/ModGameData/BPRUpgradesExpanded/` | BPRUE-owned prototypes and generated mod data |

**Do not add documentation files below `GameLite/`.** Everything there belongs to the mod/game-data tree and may be packaged into the mod.

## Generating the CFG files

The central entry point is:

```powershell
cd Python
python generate_all_cfg.py
```

Do not normally edit generated CFG files by hand. Change the corresponding JSON/Python source and regenerate instead.

The central generator builds the unified upgrade model, applies layout rules and writes the consolidated BaseGame, BPRUE-owned and DLC outputs. Among others this includes:

- `GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg`
- `GameLite/GameData/WeaponData/WeaponGeneralSetupPrototypes/WeaponGeneralSetupPrototypes_patch_BPRUE.cfg`
- `GameLite/GameData/ItemPrototypes/WeaponPrototypes/WeaponPrototypes_patch_BPRUE.cfg`
- `GameLite/ModGameData/BPRUpgradesExpanded/ItemPrototypes/WeaponPrototypes/BPRUE_WeaponPrototypes.cfg`
- `GameLite/GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE.cfg`
- DLC-specific upgrade, GeneralSetup, weapon and effect patches under `GameLite/DLCGameData/<pack>/`

See `Python/README.md` and `Python/CFGGenerators/README.md` for the source-to-output flow.

## How the upgrade data fits together

The per-class JSON files describe which weapon families participate. The Python generators turn those configurations into `UpgradeDefinition` objects. The common generator layer then combines them into one model, assigns layouts, renders upgrade prototypes and registers those upgrades with the appropriate weapon GeneralSetups and technicians.

This means a generated CFG may be affected by more than one source file. For example, technician registrations are derived from the complete model rather than being maintained as a separate hand-written list.

## SMG pistol-slot conversion

SMG pistol-slot conversion uses BPRUE-owned weapon variants because `ItemSlotType` could not be changed reliably through the normal CFG upgrade-effect system.

Each conversion variant inherits its BaseGame weapon and changes the equipment slot to `Pistol`. The generator also mirrors the source weapon's required BPRUE upgrade-section overrides into the BPRUE-owned prototype. Some systems use concrete weapon SIDs rather than inheritance, so conversion compatibility also has to account for attachment whitelists and localization.

See `Python/CFGGenerators/SMGs/README.md` for the details.

## Analysis

The scripts under `Python/Analysis/` inspect vanilla/BPRUE layouts, weapon coverage, technician mappings, DLC output and unique-weapon/signature data. Generated analysis JSON belongs under `Python/Analysis/Reports/`.

See `Python/Analysis/README.md` for the individual tools.
