# OXA tooling

## Complete generation pipeline

Run from the repository root (also works from other working directories):

```bash
python Python/OXA/generate_all_oxa.py
```

This runs, in dependency order:

1. Normal BPRUE generation (BaseGame, DLC and Editions).
2. OXA weapon discovery and upgrade-tree inventory.
3. Three-way BPRUE/Vanilla/OXA conflict analysis.
4. Base OXA compatibility CFG generation.
5. OXA-only weapon family integration (AKS-74N G2, Glock 17, P30L).
6. Edition compatibility projections based on the generated base compatibility arrays.
7. Base compatibility validation, then Edition validation.

Use `--skip-base` to reuse already-generated BPRUE CFGs, or
`--no-validate` to regenerate the OXA outputs while investigating known
validator failures. By default the pipeline stops at the first failed step
and exits nonzero; **it does not silently treat existing compatibility
mismatches as valid**.

## Directory layout

- `Analysis/`: discover OXA-only weapon prototypes and reconstruct effective upgrade/attachment structure.
- `CFGGenerators/`: OXA-specific BPRUE integration generators.
- `Reports/`: generated OXA inventory and tree reports, not hand-maintained data.

The shared Vanilla/OXA conflict analyzer and base compatibility generator
remain in `Python/Analysis` and `Python/CFGGenerators/Common`.
