from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "Python/Analysis/Reports/oxa_conflicts.json"
DEFAULT_VANILLA = ROOT / "Python/VanillaReference"
DEFAULT_OUTPUT = ROOT / "Compat/OXA/GameLite"

ARRAY_TARGETS = {
    "UpgradePrototypeSIDs": (
        "WeaponGeneralSetupPrototypes",
        "WeaponData/WeaponGeneralSetupPrototypes",
    ),
    "FittingWeaponsSIDs": (
        "AttachPrototypes",
        "ItemPrototypes/AttachPrototypes",
    ),
    "CompatibleAttachments": (
        "WeaponGeneralSetupPrototypes",
        "WeaponData/WeaponGeneralSetupPrototypes",
    ),
}

# Ambiguous OXA removenodes are intentionally not guessed by the generator.
# They remain visible in the analyzer report until explicitly resolved.
BLOCK_UNRESOLVED_REMOVALS = True


def _vanilla_scope_for(prototype: str, array: str, vanilla_root: Path) -> str:
    filename, relative_dir = ARRAY_TARGETS[array]

    dlc1 = vanilla_root / "DLCGameData/DLC1"
    if dlc1.exists():
        for path in dlc1.rglob("*.cfg"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if f"{prototype} : struct.begin" in text:
                return f"DLCGameData/DLC1/{relative_dir}"

    # Base-game reference files are flattened in VanillaReference, while the
    # actual runtime hierarchy is GameLite/GameData/<prototype family>/.
    return f"GameData/{relative_dir}"


def _render_array(prototype: str, array: str, values: list[str]) -> str:
    lines = [
        f"{prototype} : struct.begin {{bpatch}}",
        f"   {array} : struct.begin",
    ]
    for index, value in enumerate(values):
        lines.append(f"      [{index}] = {value}")
    lines += [
        "   struct.end",
        "struct.end",
        "",
    ]
    return "\n".join(lines)


def _target_file(scope: str, array: str) -> Path:
    filename, _ = ARRAY_TARGETS[array]
    return Path(scope) / f"{filename}_patch_BPRUE_OXA.cfg"


def generate(report: dict, vanilla_root: Path, output_root: Path) -> tuple[list[Path], list[dict]]:
    unresolved = {
        (item["prototype"], item["array"])
        for item in report.get("removal_identity_mismatches", {}).get("records", [])
        if item.get("resolution") == "unresolved_comment_identity"
    }

    by_file: dict[Path, list[dict]] = defaultdict(list)
    skipped: list[dict] = []

    for item in report["three_way"]:
        array = item["array"]
        if array not in ARRAY_TARGETS:
            continue

        key = (item["prototype"], array)
        if BLOCK_UNRESOLVED_REMOVALS and key in unresolved:
            skipped.append({
                "prototype": item["prototype"],
                "array": array,
                "reason": "unresolved OXA removenode identity",
            })
            continue

        # Only emit a compatibility patch when BPRUE contributes something
        # beyond Vanilla. Pure OXA changes do not belong in this mod.
        if not item["bprue_additions"]:
            continue

        scope = _vanilla_scope_for(item["prototype"], array, vanilla_root)
        by_file[_target_file(scope, array)].append(item)

    written = []
    for relative_path, items in sorted(by_file.items(), key=lambda pair: str(pair[0])):
        target = output_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            "// -----------------------------------------------------------------------------",
            "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
            "// BPRUE <-> OXA compatibility patch",
            "// Effective state: OXA + (BPRUE - Vanilla)",
            "// -----------------------------------------------------------------------------",
            "",
        ]
        for item in sorted(items, key=lambda value: (value["prototype"], value["array"])):
            lines.append(_render_array(
                item["prototype"],
                item["array"],
                item["compatibility_candidate"],
            ))

        target.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        written.append(target)

    return written, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate CFG-only BPRUE compatibility patches for OXA."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    written, skipped = generate(report, args.vanilla_root, args.output_root)

    print("BPRUE <-> OXA compatibility generator")
    print("=====================================")
    for path in written:
        print(f"Wrote {path.relative_to(ROOT).as_posix()}")

    if skipped:
        print("\nSkipped ambiguous OXA removals:")
        for item in skipped:
            print(f"  {item['prototype']} :: {item['array']} - {item['reason']}")

    print(f"\nGenerated files: {len(written)}")
    print(f"Skipped groups: {len(skipped)}")


if __name__ == "__main__":
    main()
