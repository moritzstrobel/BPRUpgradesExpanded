# Python tooling

This directory contains the editable source data, generators, validation and analysis tooling behind BPRUE. If you want to change generated CFG behavior, this is usually where to start.

## Main workflow

Run the central generator from this directory:

```powershell
python generate_all_cfg.py
```

`generate_all_cfg.py` builds one unified upgrade model from all supported weapon classes and shared/unique/DLC definitions. It then renders the CFG files below `GameLite/`.

### Source -> generator -> generated data

| Source/config | Python code | Main generated data |
| --- | --- | --- |
| `CFGGenerators/AssaultRifles/assault_rifles_upgrades.json` | `generate_assault_rifle_upgrades.py` | AR upgrades/effects through the central generator |
| `CFGGenerators/SMGs/smg_upgrades.json` | `generate_smg_upgrades.py` | SMG upgrades/effects and conversion upgrade definitions |
| `CFGGenerators/Shotguns/shotgun_upgrades.json` | `generate_shotgun_upgrades.py` | Shotgun upgrades/effects |
| `CFGGenerators/Pistols/pistol_upgrades.json` | `generate_pistol_upgrades.py` | Pistol upgrades/effects |
| `CFGGenerators/Snipers/sniper_upgrades.json` | `generate_sniper_upgrades.py` | Sniper upgrades/effects |
| `CFGGenerators/MachineGuns/machine_gun_upgrades.json` | `generate_machine_gun_upgrades.py` | Machine-gun upgrades/effects |
| `CFGGenerators/Common/unique_weapons.json` | `unique_weapon_modules.py` | Unique-weapon module instances |
| `CFGGenerators/Common/unique_signatures.json` | `unique_weapon_modules.py` | Unique signature upgrades/effects |
| `CFGGenerators/Common/dlc_weapons.json` | `dlc_weapon_modules.py` | DLC weapon mappings |
| `CFGGenerators/Common/dlc_signatures.json` | `dlc_weapon_modules.py` | DLC signature mappings |

The central renderer consolidates these definitions. Older per-class output constants may still exist in individual generator modules; the authoritative normal workflow is `generate_all_cfg.py`.

## Directories

- `CFGGenerators/` — upgrade model creation and CFG rendering.
- `Analysis/` — inspection/audit scripts; output goes to `Analysis/Reports/`.
- `Localization/` — localization JSON and validation.
- `Config/` — configuration for additional non-upgrade generators.
- `VanillaReference/` — reference copies of BaseGame/DLC CFG data used to resolve inheritance, layouts, attachments, technicians and other vanilla state.

## Editing rule of thumb

If a CFG starts with `AUTO-GENERATED FILE - DO NOT EDIT BY HAND`, find its Python/JSON source instead of fixing the generated file directly. A hand edit will be lost the next time the generator runs.

Files below `GameLite/` are game/mod data. Documentation belongs here in `Python/` or at repository root, not inside `GameLite/`.
