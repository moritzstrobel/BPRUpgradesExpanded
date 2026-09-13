from pathlib import Path
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent

GENERATORS = [
    SCRIPT_DIR / "CFGGenerators" / "Weapons" / "generate_assault_rifle_upgrades.py",
]

def main() -> None:
    for generator in GENERATORS:
        print(f"Running {generator.relative_to(SCRIPT_DIR)}")
        subprocess.run([sys.executable, str(generator)], check=True)

if __name__ == "__main__":
    main()
