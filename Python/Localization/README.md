# Localization tooling

This directory is the editable localization source for BPRUE. Localization text is maintained in JSON here and then imported into the Zone Kit localization asset. Do **not** maintain the generated/game-side localization by hand.

## Localization source files

The current localization pipeline reads these JSON files:

- `Blueprint_Localization.json`
- `Conversion_Localization.json`
- `Weapon_Module_Localization.json`
- `Kora_Localization.json`
- `MachineGun_Localization.json`
- `Shared_Specialization_Localization.json`
- `Stock_Localization.json`
- `Effect_Localization.json`
- `Unique_Localization.json`
- `Unique_Sniper_Localization.json`
- `Unique_MachineGun_Localization.json`
- `DLC1_Localization.json`

Each file contains an `entries` array. An entry has a localization SID and a `languages` object. The validation currently requires both **English** and **Russian** text for every managed entry.

Keep SIDs unique across all localization JSON files.

## Importing into Zone Kit

`generate_localization_upsert.py` is the Zone Kit/Unreal-side importer.

It reads all managed JSON sources and updates the localization asset:

`/BPRUpgradesExpanded/Localization/L_BPRUpgradesExpanded`

The importer:

- updates existing managed SIDs;
- adds missing managed SIDs;
- preserves localization entries that are not managed by these JSON files;
- checks for duplicate/missing SIDs;
- saves the asset;
- reloads and verifies the saved language values.

It must run in the Zone Kit Python environment because it imports the `unreal` module.

The localization asset must already contain at least one temporary/real entry; the importer uses an existing struct as the template for adding new entries because Zone Kit does not expose a public constructor for that struct type.

## Validation

Run the repository-side validator with:

```powershell
cd Python
python Localization/validate_localization.py
```

`validate_localization.py` checks more than the JSON syntax. It audits:

- duplicate localization SIDs;
- missing required English/Russian values;
- text/hint SIDs referenced by the generated BPRUE upgrade model;
- BPRUE localization SIDs referenced from generated CFG files;
- visible upgrade effects and their effective localization;
- BaseGame and DLC upgrade models;
- the exported localization-asset snapshot.

The report is written to:

`Python/Analysis/Reports/localization_audit.json`

The validator exits with an error when localization problems are found.

## Asset snapshot

The validator expects:

`Python/Analysis/Reports/localization_asset_snapshot.json`

This snapshot represents the localization asset state exported from Zone Kit and allows the repository-side validator to compare source JSON against the actual asset data. If the snapshot is missing, validation deliberately reports an error rather than assuming that the asset is correct.

After changing localization, the intended flow is therefore:

1. Edit the appropriate JSON source in this directory.
2. Run the Zone Kit localization upsert.
3. Export/refresh the localization asset snapshot.
4. Run `validate_localization.py`.
5. Check `localization_audit.json` if validation reports a problem.

## Conversion weapon localization

`Conversion_Localization.json` also contains aliases needed by the SMG pistol-slot conversion variants.

Those converted weapons use new BPRUE weapon SIDs. Some game UI/attachment code derives localization keys from the concrete weapon SID rather than following the source weapon's `LocalizationSID`. The aliases therefore make names such as the converted Viper/Bucket/Zubr/Fora variants resolve correctly in those contexts.

The Fora 230 is also a special case at prototype level: its vanilla localization SID is `nwpack_GunFora230_PP`, not simply `GunFora230_PP`.

## Adding a new localization source file

Adding a JSON file to this directory is not enough by itself. If it should participate in the managed localization pipeline, add it to `LOCALIZATION_FILES` in both:

- `generate_localization_upsert.py`
- `validate_localization.py`

This keeps import and validation based on the same source set.
