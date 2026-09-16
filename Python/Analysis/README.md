# Analysis tooling

This directory contains repository analysis scripts. Keep executable analysis tools at this level and generated JSON artifacts under `Reports/` so scripts and results are not mixed together.

## Upgrade layout / map tools

- `build_vanilla_upgrade_map.py` — builds the Vanilla GeneralSetup/upgrade layout map.
- `build_bprue_upgrade_map.py` — builds the generated BPRUE layout map.
- `compare_upgrade_maps.py` — compares Vanilla modifications with BPRUE layout slots.
- `analyze_upgrade_layouts.py` — performs higher-level structural layout checks.
- `analyze_weapon_upgrade_sections.py` — inspects Vanilla weapon `SectionSettings` for configured BPRUE weapons.

## Weapon coverage

- `analyze_weapon_coverage.py` — compares Vanilla weapon GeneralSetups with the weapon families configured in BPRUE. It separates likely unique/special/variant candidates from `suspected_missing` weapons instead of treating a raw SID diff as authoritative. Use `--show-excluded` to inspect the filtered candidates as well.

The coverage report is deliberately conservative: `suspected_missing` means "worth inspecting", not "confirmed missing". Likewise, unique/variant exclusions remain in the JSON report so the filter can be audited.

## Reports

Generated/snapshotted JSON reports live in `Reports/`:

- `vanilla_upgrade_map.json`
- `bprue_upgrade_map.json`
- `upgrade_map_comparison.json`
- `upgrade_layout_analysis.json`
- `weapon_upgrade_sections.json`
- `weapon_coverage.json`

New analysis tools should follow the same rule: code in `Analysis/`, generated data in `Analysis/Reports/`.
