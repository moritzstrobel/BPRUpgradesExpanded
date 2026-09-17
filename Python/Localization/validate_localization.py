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
    LOCALIZATION_DIR / "Conversion_Localization.json",
    LOCALIZATION_DIR / "Weapon_Module_Localization.json",
    LOCALIZATION_DIR / "Kora_Localization.json",
    LOCALIZATION_DIR / "MachineGun_Localization.json",
    LOCALIZATION_DIR / "Shared_Specialization_Localization.json",
    LOCALIZATION_DIR / "Stock_Localization.json",
    LOCALIZATION_DIR / "Effect_Localization.json",
    LOCALIZATION_DIR / "Unique_Localization.json",
    LOCALIZATION_DIR / "Unique_Sniper_Localization.json",
)
VANILLA_EFFECTS = PYTHON_ROOT / "VanillaReference" / "EffectPrototypes.cfg"
VANILLA_UI_PATCH = REPO_ROOT / "GameLite/GameData/EffectPrototypes/EffectPrototypes_patch_BPRUE_UI.cfg"
BPRUE_EFFECT_DIR = REPO_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes"

EFFECT_SID_RE = re.compile(r"^\s*LocalizationSID\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)
SHOW_RE = re.compile(r"^\s*ShowUpgradeEffect\s*=\s*(true|false)\s*$", re.MULTILINE | re.IGNORECASE)
REFKEY_RE = re.compile(r"\brefkey=([^}\s]+)")
PROTOTYPE_RE = re.compile(r"(?ms)^([A-Za-z0-9_]+)\s*:\s*struct\.begin([^\n]*)\n(.*?)^struct\.end")


def load_localization_sids() -> set[str]:
    result: set[str] = set(); duplicates: set[str] = set()
    for path in LOCALIZATION_FILES:
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            sid = entry["sid"]
            if sid in result: duplicates.add(sid)
            result.add(sid)
    if duplicates: raise ValueError("Duplicate localization SIDs: " + ", ".join(sorted(duplicates)))
    return result


def effect_asset_sid(cfg_sid: str) -> str: return f"sid_effects_{cfg_sid}_name"


def audit_upgrade_model(model, localization_sids: set[str]) -> dict:
    text_sids: set[str] = set(); hint_sids: set[str] = set(); missing: set[str] = set()
    for upgrade in model.upgrades:
        for kind, sid in (("text", upgrade.text_sid), ("hint", upgrade.hint_sid)):
            if not sid or not sid.startswith("sid_bprue_"): continue
            (text_sids if kind == "text" else hint_sids).add(sid)
            if sid not in localization_sids: missing.add(sid)
    return {"upgrade_count": len(model.upgrades), "text_sid_count": len(text_sids), "hint_sid_count": len(hint_sids), "missing_count": len(missing), "missing_sids": sorted(missing)}


def _parse_effects(path: Path, source: str) -> dict[str, dict]:
    if not path.exists(): return {}
    result = {}
    for sid, header, body in PROTOTYPE_RE.findall(path.read_text(encoding="utf-8")):
        ref = REFKEY_RE.search(header); show = SHOW_RE.search(body); loc = EFFECT_SID_RE.search(body)
        result[sid] = {"sid": sid, "source": source, "refkey": ref.group(1) if ref else None, "show": show.group(1).lower() == "true" if show else None, "localization_sid": loc.group(1) if loc else None}
    return result


def _effect_catalog() -> dict[str, dict]:
    catalog = _parse_effects(VANILLA_EFFECTS, "BaseGame")
    for path in sorted(BPRUE_EFFECT_DIR.glob("*.cfg")): catalog.update(_parse_effects(path, path.name))
    catalog.update(_parse_effects(VANILLA_UI_PATCH, VANILLA_UI_PATCH.name))
    return catalog


def _effective_effect(sid: str, catalog: dict[str, dict]) -> dict:
    current = sid; seen = set(); show = None; localization_sid = None; chain = []; sources = []
    while current and current not in seen:
        seen.add(current); entry = catalog.get(current)
        if not entry: break
        chain.append(current); sources.append(entry["source"])
        if show is None and entry["show"] is not None: show = entry["show"]
        if localization_sid is None and entry["localization_sid"]: localization_sid = entry["localization_sid"]
        ref = entry["refkey"]; current = ref if ref and ref != "[0]" else None
    return {"resolved": bool(chain), "chain": chain, "sources": sources, "visible": show is not False, "localization_sid": localization_sid}


def _is_bprue_localization(localization_sid: str) -> bool:
    return localization_sid.lower().startswith("bprue_")


def audit_referenced_effects(models: dict[str, object], localization_sids: set[str]) -> dict:
    catalog = _effect_catalog(); references: dict[str, set[str]] = defaultdict(set)
    for scope, model in models.items():
        for upgrade in model.upgrades:
            for effect_sid in upgrade.effects: references[effect_sid].add(scope)

    errors = []; rows = []
    for sid in sorted(references):
        effective = _effective_effect(sid, catalog); scopes = sorted(references[sid]); status = "ok"
        if not effective["resolved"]:
            status = "unresolved"; errors.append(f"{sid}: referenced by {', '.join(scopes)} but no effect prototype could be resolved")
        elif effective["visible"]:
            loc = effective["localization_sid"]
            if not loc:
                status = "visible_without_localization"; errors.append(f"{sid}: visible effect referenced by {', '.join(scopes)} has no effective LocalizationSID")
            elif _is_bprue_localization(loc) and effect_asset_sid(loc) not in localization_sids:
                status = "missing_bprue_localization_asset"; errors.append(f"{sid}: visible BPRUE effect references missing localization {effect_asset_sid(loc)} ({', '.join(scopes)})")
            elif not _is_bprue_localization(loc):
                status = "vanilla_localization"
        rows.append({"sid": sid, "scopes": scopes, "visible": effective["visible"], "localization_sid": effective["localization_sid"], "resolution_chain": effective["chain"], "sources": effective["sources"], "status": status})
    return {"referenced_effect_count": len(rows), "visible_effect_count": sum(row["visible"] for row in rows if row["status"] != "unresolved"), "vanilla_localization_count": sum(row["status"] == "vanilla_localization" for row in rows), "error_count": len(errors), "errors": errors, "effects": rows}


def main() -> None:
    localization_sids = load_localization_sids()
    base_model, configs = build_model(apply_layout=False); dlc_models = build_dlc_outputs(base_model, configs)
    models = {"BaseGame": base_model, **dlc_models}
    scopes = {scope: audit_upgrade_model(model, localization_sids) for scope, model in models.items()}
    effects = audit_referenced_effects(models, localization_sids)
    missing_by_sid: dict[str, list[str]] = defaultdict(list)
    for scope, audit in scopes.items():
        for sid in audit["missing_sids"]: missing_by_sid[sid].append(scope)

    report = {"localization_sid_count": len(localization_sids), "scopes": scopes, "effects": effects, "unique_missing_upgrade_sid_count": len(missing_by_sid), "missing_upgrade_sids": {sid: affected for sid, affected in sorted(missing_by_sid.items())}, "error_count": len(missing_by_sid) + effects["error_count"]}
    REPORT_DIR.mkdir(parents=True, exist_ok=True); report_path = REPORT_DIR / "localization_audit.json"; report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Localization SIDs: {len(localization_sids)}")
    for scope, audit in scopes.items(): print(f"{scope}: upgrades={audit['upgrade_count']} text={audit['text_sid_count']} hints={audit['hint_sid_count']} missing={audit['missing_count']}")
    print(f"Effects: referenced={effects['referenced_effect_count']} visible={effects['visible_effect_count']} vanilla-localized={effects['vanilla_localization_count']} errors={effects['error_count']}")
    print(f"Total localization errors: {report['error_count']}")
    print(f"Report: {report_path}")
    if report["error_count"]: raise SystemExit(1)


if __name__ == "__main__": main()
