"""Regenerate the complete OXA compatibility package in dependency order.

Run from any working directory:
    python Python/OXA/generate_all_oxa.py
    python Python/OXA/generate_all_oxa.py --skip-base
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Order matters: the conflict report consumes generated BPRUE CFGs; the base
# compatibility patch consumes that report; Edition projections consume the
# base compatibility arrays. Validate each product only after it exists.
BASE_GENERATION = [
    "Python/generate_all_cfg.py",
]
OXA_DISCOVERY = [
    "Python/OXA/Analysis/analyze_oxa_weapons.py",
    "Python/OXA/Analysis/analyze_oxa_upgrade_trees.py",
]
COMPAT_GENERATION = [
    "Python/Analysis/analyze_oxa_conflicts.py",
    "Python/CFGGenerators/Common/generate_oxa_compat.py",
    "Python/OXA/CFGGenerators/generate_oxa_weapon_upgrades.py",
    "Python/OXA/CFGGenerators/generate_oxa_edition_compat.py",
]
VALIDATION = [
    "Python/Analysis/validate_oxa_compat.py",
    "Python/OXA/Analysis/validate_oxa_edition_compat.py",
]


def run(script: str, number: int, total: int) -> None:
    path = ROOT / script
    if not path.is_file():
        raise FileNotFoundError(f"Missing pipeline script: {path}")
    print(f"\n[{number}/{total}] {script}", flush=True)
    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and validate all BPRUE/OXA compatibility CFGs.")
    parser.add_argument(
        "--skip-base", action="store_true",
        help="Reuse existing BaseGame/DLC/Edition CFGs instead of regenerating them.",
    )
    parser.add_argument(
        "--no-validate", action="store_true",
        help="Generate all outputs without running the compatibility validators.",
    )
    args = parser.parse_args()
    steps = (
        ([] if args.skip_base else BASE_GENERATION)
        + OXA_DISCOVERY
        + COMPAT_GENERATION
        + ([] if args.no_validate else VALIDATION)
    )
    for index, script in enumerate(steps, 1):
        try:
            run(script, index, len(steps))
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            parser.exit(1, f"\nOXA pipeline stopped at {script}: {exc}\n")
    print("\nOXA pipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main()
