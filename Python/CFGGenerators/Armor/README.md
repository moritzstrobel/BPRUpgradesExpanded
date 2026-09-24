# BPRUE Armor module

Optional armor-upgrade module for BPR Upgrades Expanded.

## Goals

- Ship armor upgrades separately from BPRUE Main.
- Treat existing `Python/Analysis/Armor-Upgrades` work as research/input rather than copying it directly.
- Generate armor integration from structured source data.
- Prefer targeted, merge-friendly patches over broad replacement of Vanilla armor data.
- Keep armor balancing and releases independent from the weapon-upgrade module.

## Planned structure

- `armor_upgrades.json` — declarative armor upgrade/module definitions.
- `generate_armor_upgrades.py` — armor model/generator entry point.
- common renderers/helpers only where they are genuinely shared with Main.

Generated output will live below `Armor/GameLite` so it can be packaged independently.
