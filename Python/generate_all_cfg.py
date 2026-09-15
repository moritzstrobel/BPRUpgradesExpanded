from pathlib import Path
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent

# Class generators first create model-backed class outputs. The remaining
# finalizers only perform concerns that require the complete generated set:
# SMG attachment wiring, layout/consolidation, vanilla GeneralSetup replacement,
# technician consolidation, and finally cross-output validation.
GENERATORS = [
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "generate_assault_rifle_upgrades.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "generate_smg_upgrades.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "merge_smg_weapon_patches.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "generate_shotgun_upgrades.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "generate_pistol_upgrades.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "generate_sniper_upgrades.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "merge_upgrade_prototypes.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "merge_weapon_general_setup_patches.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "merge_technician_conversion_upgrades.py",
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "validate_generated_upgrade_outputs.py",
]


def main() -> None:
    for generator in GENERATORS:
        print(f"Running {generator.relative_to(SCRIPT_DIR)}")
        subprocess.run([sys.executable, str(generator)], check=True)


if __name__ == "__main__":
    main()
