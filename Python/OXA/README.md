# OXA tooling

OXA-specific analysis and generation lives here so the Vanilla/BPRUE tooling under
`Python/Analysis` and `Python/CFGGenerators` can keep its existing structure and
assumptions.

## Planned structure

- `Analysis/` - discover OXA-only weapon prototypes and reconstruct their effective
  upgrade/attachment structure.
- `CFGGenerators/` - OXA-specific BPRUE integration generators once the discovered
  weapon trees are understood.
- `Reports/` - generated OXA inventory/tree reports; no hand-maintained source data.

The existing OXA compatibility pipeline remains where it is for now. This directory is
for extending BPRUE onto OXA-provided weapons, not for moving or rewriting the proven
Vanilla/OXA compatibility tooling.
