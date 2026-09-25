from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parent
COMMON = PYTHON_ROOT / "CFGGenerators" / "Common"
sys.path.insert(0, str(PYTHON_ROOT))
sys.path.insert(0, str(COMMON))

from analysis_paths import REPORTS_DIR
from generate_all_cfg import (
    EDITIONS_OUTPUT_ROOT,
    build_edition_outputs,
    build_model,
    render_weapon_sections_patch,
)
from upgrade_renderers import render_consolidated_upgrade_prototypes, render_dlc_general_setup_patch
from vanilla_upgrade_layout import available_target_parts, dlc_general_setup_upgrades
from edition_weapon_modules import load_edition_config

REPORT_PATH = REPORTS_DIR / "edition_output_audit.json"
BASE_EFFECT_DIR = PYTHON_ROOT.parent / "GameLite" / "ModGameData" / "BPRUpgradesExpanded" / "EffectPrototypes"
SID_DEF_RE = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*:\s*struct\.begin")
SETUP_BLOCK_RE = re.compile(r"(?ms)^([A-Za-z0-9_]+)\s*:\s*struct\.begin\s*\{bpatch\}\s*\n(.*?)(?=^[A-Za-z0-9_]+\s*:\s*struct\.begin\s*\{bpatch\}|\Z)")
UPGRADE_ARRAY_RE = re.compile(r"(?ms)^\s*UpgradePrototypeSIDs\s*:\s*struct\.begin\s*\n(.*?)^\s*struct\.end")
ARRAY_VALUE_RE = re.compile(r"^\s*\[\d+\]\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)


def _known_effect_sids() -> set[str]:
    result: set[str] = set()
    for path in sorted(BASE_EFFECT_DIR.glob("*.cfg")):
        result.update(SID_DEF_RE.findall(path.read_text(encoding="utf-8")))
    vanilla = PYTHON_ROOT / "VanillaReference" / "EffectPrototypes.cfg"
    if vanilla.exists():
        result.update(SID_DEF_RE.findall(vanilla.read_text(encoding="utf-8")))
    return result


def _setup_arrays(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for sid, body in SETUP_BLOCK_RE.findall(text):
        match = UPGRADE_ARRAY_RE.search(body)
        if match:
            result[sid] = ARRAY_VALUE_RE.findall(match.group(1))
    return result


def _expected_weapons_by_pack() -> dict[str, dict[str, dict]]:
    result: dict[str, dict[str, dict]] = defaultdict(dict)
    for name, entry in load_edition_config().get("weapons", {}).items():
        result[entry["content_pack"]][name] = entry
    return dict(result)


def _output_paths(pack: str) -> dict[str, Path]:
    root = EDITIONS_OUTPUT_ROOT / pack
    return {
        "upgrades": root / "UpgradePrototypes" / "UpgradePrototypes_patch_BPRUE.cfg",
        "general_setup": root / "WeaponData" / "WeaponGeneralSetupPrototypes" / "WeaponGeneralSetupPrototypes_patch_BPRUE.cfg",
        "sections": root / "ItemPrototypes" / "ItemPrototypes_patch_BPRUE.cfg",
    }


def _validate_phase2_path(path: Path, prototype_name: str) -> str | None:
    if path.parent.name != prototype_name:
        return f"{path}: patch must be inside a '{prototype_name}' folder"
    if not path.name.startswith(f"{prototype_name}_patch_"):
        return f"{path}: patch filename must start with '{prototype_name}_patch_'"
    return None


def main() -> None:
    source_model, configs = build_model(apply_layout=False)
    dlc_models = build_edition_outputs(source_model, configs)
    expected_by_pack = _expected_weapons_by_pack()
    known_effects = _known_effect_sids()
    all_generated_sids = [u.sid for model in dlc_models.values() for u in model.upgrades]
    duplicate_sids = sorted(sid for sid, count in Counter(all_generated_sids).items() if count > 1)
    errors: list[str] = []
    packs: dict[str, dict] = {}

    expected_pack_names = set(expected_by_pack)
    actual_pack_names = set(dlc_models)
    for pack in sorted(expected_pack_names - actual_pack_names):
        errors.append(f"{pack}: expected Edition pack has no generated model")
    for pack in sorted(actual_pack_names - expected_pack_names):
        errors.append(f"{pack}: generated Edition pack is not present in edition_weapons.json")

    for pack in sorted(expected_pack_names | actual_pack_names):
        model = dlc_models.get(pack)
        expected_weapons = expected_by_pack.get(pack, {})
        if model is None:
            packs[pack] = {"expected_weapons": len(expected_weapons), "generated_setups": 0, "errors": ["missing generated model"]}
            continue

        model.validate()
        by_setup = model.by_general_setup()
        source_arrays = dlc_general_setup_upgrades(pack)
        upgrade_text = render_consolidated_upgrade_prototypes(model)
        setup_text = render_dlc_general_setup_patch(model, pack)
        section_text = render_weapon_sections_patch(model, content_pack=pack)
        rendered_arrays = _setup_arrays(setup_text)
        rendered_defs = Counter(SID_DEF_RE.findall(upgrade_text))
        pack_errors: list[str] = []

        expected_setups = {entry["general_setup_sid"] for entry in expected_weapons.values()}
        generated_setups = set(by_setup)
        for sid in sorted(expected_setups - generated_setups):
            pack_errors.append(f"{sid}: configured Edition weapon has no generated upgrades")
        for sid in sorted(generated_setups - expected_setups):
            pack_errors.append(f"{sid}: generated setup is not registered in dlc_weapons.json")

        prototype_missing = 0
        registration_errors = 0
        retention_errors = 0
        blocking_errors = 0
        effect_errors = 0
        section_errors = 0

        known_pack_upgrades = {u.sid for u in model.upgrades}
        for upgrade in model.upgrades:
            if rendered_defs[upgrade.sid] != 1:
                prototype_missing += 1
                pack_errors.append(f"{upgrade.sid}: rendered prototype count is {rendered_defs[upgrade.sid]}, expected 1")
            unknown_blocks = [sid for sid in upgrade.blocking_sids if sid not in known_pack_upgrades]
            if unknown_blocks:
                blocking_errors += len(unknown_blocks)
                pack_errors.append(f"{upgrade.sid}: unknown blocking refs: {', '.join(unknown_blocks)}")
            unknown_effects = [sid for sid in upgrade.effects if sid not in known_effects]
            if unknown_effects:
                effect_errors += len(unknown_effects)
                pack_errors.append(f"{upgrade.sid}: unknown effect refs: {', '.join(unknown_effects)}")
            available = set(available_target_parts(upgrade.general_setup_sid, include_disabled=True, content_pack=pack))
            if upgrade.target_part not in available:
                section_errors += 1
                pack_errors.append(f"{upgrade.sid}: target section {upgrade.target_part} does not exist on {upgrade.general_setup_sid}")

        for setup_sid, upgrades in by_setup.items():
            rendered = rendered_arrays.get(setup_sid)
            if rendered is None:
                registration_errors += len(upgrades)
                pack_errors.append(f"{setup_sid}: no rendered UpgradePrototypeSIDs array")
                continue
            source = source_arrays.get(setup_sid, [])
            missing_source = [sid for sid in source if sid not in rendered]
            if missing_source:
                retention_errors += len(missing_source)
                pack_errors.append(f"{setup_sid}: source upgrades not retained: {', '.join(missing_source)}")
            missing_generated = [u.sid for u in upgrades if u.sid not in rendered]
            if missing_generated:
                registration_errors += len(missing_generated)
                pack_errors.append(f"{setup_sid}: generated upgrades not registered: {', '.join(missing_generated)}")
            duplicates = sorted(sid for sid, count in Counter(rendered).items() if count > 1)
            if duplicates:
                pack_errors.append(f"{setup_sid}: duplicate GeneralSetup upgrade refs: {', '.join(duplicates)}")

        paths = _output_paths(pack)
        prototype_names = {"upgrades": "UpgradePrototypes", "general_setup": "WeaponGeneralSetupPrototypes", "sections": "ItemPrototypes"}
        for name, path in paths.items():
            phase2_error = _validate_phase2_path(path, prototype_names[name])
            if phase2_error:
                pack_errors.append(phase2_error)
        path_state = {name: {"path": str(path.relative_to(PYTHON_ROOT.parent)), "exists": path.exists()} for name, path in paths.items()}
        expected_texts = {"upgrades": upgrade_text, "general_setup": setup_text, "sections": section_text}
        for name, path in paths.items():
            if not path.exists():
                pack_errors.append(f"missing generated output: {path.relative_to(PYTHON_ROOT.parent)}")
            elif path.read_text(encoding="utf-8") != expected_texts[name]:
                pack_errors.append(f"stale generated output: {path.relative_to(PYTHON_ROOT.parent)}")

        packs[pack] = {
            "expected_weapons": len(expected_weapons),
            "generated_setups": len(generated_setups),
            "generated_upgrades": len(model.upgrades),
            "prototype_errors": prototype_missing,
            "registration_errors": registration_errors,
            "retention_errors": retention_errors,
            "blocking_reference_errors": blocking_errors,
            "effect_reference_errors": effect_errors,
            "section_errors": section_errors,
            "output_files": path_state,
            "errors": pack_errors,
        }
        errors.extend(f"{pack}: {error}" for error in pack_errors)

    if duplicate_sids:
        errors.append("duplicate generated Edition upgrade SIDs across packs: " + ", ".join(duplicate_sids))

    total_expected_weapons = sum(len(entries) for entries in expected_by_pack.values())
    total_generated_setups = sum(len(model.by_general_setup()) for model in dlc_models.values())
    total_upgrades = sum(len(model.upgrades) for model in dlc_models.values())
    report = {
        "summary": {
            "expected_weapons": total_expected_weapons,
            "generated_setups": total_generated_setups,
            "generated_upgrades": total_upgrades,
            "duplicate_generated_sids": len(duplicate_sids),
            "known_effect_sids": len(known_effects),
            "errors": len(errors),
        },
        "packs": packs,
        "duplicate_sids": duplicate_sids,
        "errors": errors,
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Edition output audit")
    print(f"Weapons: {total_generated_setups}/{total_expected_weapons} | upgrades={total_upgrades} | duplicate SIDs={len(duplicate_sids)}")
    for pack, data in packs.items():
        print(
            f"  {pack:<10} weapons={data['generated_setups']}/{data['expected_weapons']} | "
            f"upgrades={data.get('generated_upgrades', 0)} | prototype={data.get('prototype_errors', 0)} | "
            f"registration={data.get('registration_errors', 0)} | retained={data.get('retention_errors', 0)} | "
            f"blocking={data.get('blocking_reference_errors', 0)} | effects={data.get('effect_reference_errors', 0)} | "
            f"sections={data.get('section_errors', 0)} | errors={len(data.get('errors', []))}"
        )
    print(f"Unknown/structural errors: {len(errors)}")
    print(f"Wrote {REPORT_PATH}")
    if errors:
        raise ValueError("Edition output audit failed:\n  - " + "\n  - ".join(errors))
    print("Edition output audit successful.")


if __name__ == "__main__":
    main()
