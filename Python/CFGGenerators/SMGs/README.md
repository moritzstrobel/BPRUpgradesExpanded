# SMG generator and pistol-slot conversion

The normal SMG upgrade definitions start with:

- `smg_upgrades.json` — configured SMG families/weapon data.
- `generate_smg_upgrades.py` — builds the SMG upgrade definitions and effects.

The central `Python/generate_all_cfg.py` combines those definitions with the other weapon classes and renders the final CFG output.

## Pistol-slot conversion

The conversion exists because `ItemSlotType` is a property of the weapon prototype and no reliable normal upgrade effect was found that changes it dynamically on the existing weapon.

Instead, installing the conversion changes the weapon to a BPRUE-owned variant. The variant inherits the corresponding BaseGame weapon and changes `ItemSlotType` to `EInventoryEquipmentSlot::Pistol`.

### Relevant files

- `pistol_conversion_variants.py` — source weapon SID, converted weapon SID, localization SID and conversion upgrade SID.
- `generate_smg_upgrades.py` — creates the actual conversion upgrade alongside the normal SMG modules.
- `smg_conversion_attachments.py` — preserves the source GeneralSetup's vanilla `CompatibleAttachments` entries and appends the conversion-kit attachment safely.
- `trader_conversion_kits.py` — handles trader distribution for conversion-kit items where applicable.
- `Python/generate_all_cfg.py` — renders the BPRUE-owned converted weapon prototypes and their upgrade-tree section overrides.

### Why compatibility work is necessary

Inheritance keeps the converted weapon close to vanilla, but some game systems compare concrete weapon SIDs. Therefore a new converted SID may need explicit support even though its prototype inherits the original weapon.

Current examples include:

- attachment `FittingWeaponsSIDs` compatibility;
- localization aliases for converted weapon SIDs;
- inherited upgrade-tree sections that BPRUE needs to enable;
- preservation of the vanilla `CompatibleAttachments` array when adding the conversion kit.

Do not create a separate `GeneralWeaponSetup` merely to remove/rewrite upgrades for the converted variant. The converted weapons intentionally keep the inherited BaseGame GeneralSetup because separate cloned setups caused runtime weapon/animation lookup problems.

## Generated conversion weapon prototypes

The converted weapon definitions belong to:

`GameLite/ModGameData/BPRUpgradesExpanded/ItemPrototypes/WeaponPrototypes/BPRUE_WeaponPrototypes.cfg`

They are BPRUE-owned prototypes, not BaseGame patches. Consequently their `SectionSettings` overrides are generated directly into those prototype definitions.

The normal BaseGame weapon section patches remain in:

`GameLite/GameData/ItemPrototypes/WeaponPrototypes/WeaponPrototypes_patch_BPRUE.cfg`

This keeps ownership clear: BaseGame SIDs are patched in `GameData`; BPRUE SIDs are defined in `ModGameData`.
