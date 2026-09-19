# CFG generators

This directory contains the source model for BPRUE weapon upgrades.

## Weapon-class folders

Each weapon class has a JSON configuration plus Python code that translates that configuration into upgrade definitions:

| Folder | Main config | Generator |
| --- | --- | --- |
| `AssaultRifles/` | `assault_rifles_upgrades.json` | `generate_assault_rifle_upgrades.py` |
| `SMGs/` | `smg_upgrades.json` | `generate_smg_upgrades.py` |
| `Shotguns/` | `shotgun_upgrades.json` | `generate_shotgun_upgrades.py` |
| `Pistols/` | `pistol_upgrades.json` | `generate_pistol_upgrades.py` |
| `Snipers/` | `sniper_upgrades.json` | `generate_sniper_upgrades.py` |
| `MachineGuns/` | `machine_gun_upgrades.json` | `generate_machine_gun_upgrades.py` |

The JSON answers mostly **which weapons/families and configuration values** are involved. The Python modules answer **how those values become BPRUE upgrade definitions/effects**.

## Common

`Common/` is the shared layer used by the class generators and `Python/generate_all_cfg.py`.

Important files include:

- `upgrade_build_model.py` — common `UpgradeBuildModel` / `UpgradeDefinition` representation.
- `upgrade_renderers.py` — renders consolidated upgrade, GeneralSetup and technician CFG output.
- `apply_module_layout.py` — assigns BPRUE upgrades to upgrade-tree layout slots.
- `vanilla_upgrade_layout.py` — parses/resolves vanilla upgrade and GeneralSetup data.
- `shared_upgrades.py` / `shared_effects.py` — definitions shared across weapon classes.
- `unique_weapons.json` / `unique_signatures.json` — unique-weapon registries.
- `unique_weapon_modules.py` — expands unique definitions into the model.
- `dlc_weapons.json` / `dlc_signatures.json` — DLC registries.
- `dlc_weapon_modules.py` — builds DLC-specific models/output.

## Generated output

Do not think of one Python generator as owning one final CFG. `generate_all_cfg.py` combines all class generators into a unified model and writes consolidated files, including:

- BPRUE upgrade prototypes
- BaseGame GeneralSetup registrations
- BaseGame weapon `SectionSettings` patches
- BPRUE-owned conversion weapon prototypes
- technician upgrade registrations
- effect prototypes
- DLC-specific equivalents

So when tracking a generated SID, start with the weapon-class JSON/Python file and then follow it into the common build/render pipeline.

For SMG pistol-slot conversion specifically, see `SMGs/README.md`.
