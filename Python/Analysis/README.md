# Analysis tooling

This directory contains repository analysis and audit scripts. Keep executable tools here and generated JSON artifacts under `Reports/` so scripts and results are not mixed together.

These scripts inspect the source/generator model and vanilla reference data; they are **not** runtime mod files and are not packaged below `GameLite/`.

## Upgrade layout / map tools

- `build_vanilla_upgrade_map.py` — builds the Vanilla GeneralSetup/upgrade layout map.
- `build_bprue_upgrade_map.py` — builds the BPRUE layout map from the current unified generator model.
- `compare_upgrade_maps.py` — compares Vanilla modifications with BPRUE layout slots.
- `analyze_upgrade_layouts.py` — performs higher-level structural layout checks.
- `analyze_weapon_upgrade_sections.py` — inspects Vanilla weapon `SectionSettings` for weapons configured by BPRUE.

## Weapon coverage and unique weapons

- `analyze_weapon_coverage.py` — compares Vanilla weapon GeneralSetups with BPRUE weapon-family configuration. It separates likely unique/special/variant candidates from `suspected_missing` weapons.
- `analyze_unique_weapons.py` — inspects unique weapons against the shared unique-weapon registry.
- `analyze_unique_signature_context.py` — gathers context needed to understand unique/signature weapons, including DLC data when requested.

The coverage report is deliberately conservative: `suspected_missing` means **worth inspecting**, not **confirmed missing**. Unique/variant exclusions remain visible in the JSON so the filtering can be audited.

## Technician / trader / DLC checks

- `build_technician_upgrade_map.py` — resolves technician upgrade assignments for the current BPRUE model.
- `build_trader_item_map.py` — analyzes vanilla trader/item-generator data.
- `audit_dlc_outputs.py` — checks generated DLC output against the expected DLC model/output structure.

## Reports

Generated/snapshotted JSON reports live in `Reports/`. Existing reports include:

- `vanilla_upgrade_map.json`
- `bprue_upgrade_map.json`
- `upgrade_map_comparison.json`
- `upgrade_layout_analysis.json`
- `weapon_upgrade_sections.json`
- `weapon_coverage.json`
- unique/signature analysis reports produced by the corresponding scripts

Reports are diagnostic artifacts. Do not treat an old report as authoritative after changing generator/configuration data; regenerate the relevant analysis first.

New analysis tools should follow the same rule: code in `Analysis/`, generated data in `Analysis/Reports/`.
