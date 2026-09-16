from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PYTHON_ROOT.parent
LOCALIZATION_DIR = Path(__file__).resolve().parent
REPORT_DIR = PYTHON_ROOT / "Analysis" / "Reports"
sys.path.insert(0, str(PYTHON_ROOT))

from generate_all_cfg import build_dlc_outputs, build_model

LOCALIZATION_FILES = (
    LOCALIZATION_DIR / "Blueprint_Localization.json",
    LOCALIZATION_DIR / "Weapon_Module_Localization.json",
    LOCALIZATION_DIR / "Kora_Localization.json",
    LOCALIZATION_DIR / "MachineGun_Localization.json",
    LOCALIZATION_DIR / "Shared_Specialization_Localization.json",
    LOCALIZATION_DIR / "Stock_Localization.json",
    LOCALIZATION_DIR / "Effect_Localization.json",
)

EFFECT_SID_RE = re.compile(r"^\s*LocalizationSID\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)
VISIBLE_RE = re.compile(r"^\s*ShowUpgradeEffect\s*=\s*true\s*$", re.MULTILINE | re.IGNORECASE)
PROTOTYPE_RE = re.compile(r"(?ms)^([A-Za-z0-9_]+)\s*:\s*struct\.begin[^\n]*\n(.*?)^struct\.end")


def load_localization_sids() -> set[str]:
    result: set[str] = set()
    duplicates: set[str] = set()
    for path in LOCALIZATION_FILES:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            sid = entry["sid"]
            if sid in result:
                duplicates.add(sid)
            result.add(sid)
    if duplicates:
        raise ValueError("Duplicate localization SIDs: " + ", ".join(sorted(duplicates)))
    return result


def effect_asset_sid(cfg_sid: str) -> str:
    return f"sid_effects_{cfg_sid}_name"


def audit_upgrade_model(model, localization_sids: set[str]) -> dict:
    text_sids: set[str] = set()
    hint_sids: set[str] = set()
    missing: set[str] = set()

    for upgrade in model.upgrades:
        for kind, sid in (("text", upgrade.text_sid), ("hint", upgrade.hint_sid)):
            if not sid or not sid.startswith("sid_bprue_"):
                continue
            (text_sids if kind == "text" else hint_sids).add(sid)
            if sid not in localization_sids:
                missing.add(sid)

    return {
        "upgrade_count": len(model.upgrades),
        "text_sid_count": len(text_sids),
        "hint_sid_count": len(hint_sids),
        "missing_count": len(missing),
        "missing_sids": sorted(missing),
    }


def audit_effects(localization_sids: set[str]) -> dict:
    effect_dir = REPO_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes"
    visible_count = 0
    localized_count = 0
    errors: list[str] = []

    for path in sorted(effect_dir.glob("BPRUE_*EffectPrototypes.cfg")):
        text = path.read_text(encoding="utf-8")
        for prototype_sid, body in PROTOTYPE_RE.findall(text):
            if not prototype_sid.startswith("BPRUE_") or not VISIBLE_RE.search(body):
                continue
            visible_count += 1
            match = EFFECT_SID_RE.search(body)
            if not match:
                errors.append(f"{path.name}:{prototype_sid}: visible effect has no LocalizationSID")
                continue
            asset_sid = effect_asset_sid(match.group(1))
            if asset_sid not in localization_sids:
                errors.append(f"{path.name}:{prototype_sid}: missing localization {asset_sid}")
                continue
            localized_count += 1

    return {
        "visible_effect_count": visible_count,
        "localized_effect_count": localized_count,
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> None:
    localization_sids = load_localization_sids()

    # Build from the same pre-layout source used by the real generator. DLC clones
    # deliberately reuse the base module Text/Hint SIDs, so this verifies the
    # effective upgrade population without requiring duplicate DLC localization.
    base_model, configs = build_model(apply_layout=False)
    dlc_models = build_dlc_outputs(base_model, configs)

    scopes = {"BaseGame": audit_upgrade_model(base_model, localization_sids)}
    for pack, model in sorted(dlc_models.items()):
        scopes[pack] = audit_upgrade_model(model, localization_sids)

    effects = audit_effects(localization_sids)
    missing_by_sid: dict[str, list[str]] = defaultdict(list)
    for scope, audit in scopes.items():
        for sid in audit["missing_sids"]:
            missing_by_sid[sid].append(scope)

    report = {
        "localization_sid_count": len(localization_sids),
        "scopes": scopes,
        "effects": effects,
        "unique_missing_upgrade_sid_count": len(missing_by_sid),
        "missing_upgrade_sids": {sid: scopes for sid, scopes in sorted(missing_by_sid.items())},
        "error_count": len(missing_by_sid) + effects["error_count"],
    }

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "localization_audit.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Localization audit")
    print(f"Indexed localization SIDs: {len(localization_sids)}")
    for scope, audit in scopes.items():
        print(
            f"  {scope:<10} upgrades={audit['upgrade_count']} | "
            f"TextSIDs={audit['text_sid_count']} | HintSIDs={audit['hint_sid_count']} | "
            f"missing={audit['missing_count']}"
        )
    print(
        f"  Effects    visible={effects['visible_effect_count']} | "
        f"localized={effects['localized_effect_count']} | errors={effects['error_count']}"
    )
    print(f"Unique missing upgrade SIDs: {len(missing_by_sid)}")
    print(f"Wrote {report_path}")

    errors: list[str] = []
    for sid, affected_scopes in sorted(missing_by_sid.items()):
        errors.append(f"missing upgrade localization: {sid} ({', '.join(affected_scopes)})")
    errors.extend(effects["errors"])
    if errors:
        raise ValueError("Localization validation failed:\n  - " + "\n  - ".join(errors))

    print("Localization validation successful for BaseGame, Uniques and all DLC scopes.")


if __name__ == "__main__":
    main()
