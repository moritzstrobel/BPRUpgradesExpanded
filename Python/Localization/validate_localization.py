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

from generate_all_cfg import build_dlc_outputs, build_edition_outputs, build_model

def localization_files() -> tuple[Path, ...]:
    return tuple(sorted(LOCALIZATION_DIR.glob("*_Localization.json")))

REQUIRED_LANGUAGES = ("English", "Russian", "Chinese")
VANILLA_EFFECTS = PYTHON_ROOT / "VanillaReference" / "EffectPrototypes.cfg"
VANILLA_UI_PATCH = REPO_ROOT / "GameLite/GameData/EffectPrototypes/EffectPrototypes_patch_BPRUE_UI.cfg"
ARMOR_EFFECT_PATCH = REPO_ROOT / "Armor/GameLite/GameData/EffectPrototypes/EffectPrototypes_patch_BPRUE_Armor.cfg"
BPRUE_EFFECT_DIR = REPO_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes"
DLC_EFFECT_ROOT = REPO_ROOT / "GameLite/DLCGameData"
EDITION_EFFECT_ROOT = REPO_ROOT / "Editions/GameLite/DLCGameData"
ASSET_SNAPSHOT = REPORT_DIR / "localization_asset_snapshot.json"

EFFECT_SID_RE = re.compile(r"^\s*LocalizationSID\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)
BPRUE_TEXT_SID_RE = re.compile(r"\b(?:sid_bprue|sid_item_bprue)_[A-Za-z0-9_]+\b", re.IGNORECASE)
SHOW_RE = re.compile(r"^\s*ShowUpgradeEffect\s*=\s*(true|false)\s*$", re.MULTILINE | re.IGNORECASE)
REFKEY_RE = re.compile(r"\brefkey=([^}\s]+)")
PROTOTYPE_RE = re.compile(r"(?ms)^([A-Za-z0-9_]+)\s*:\s*struct\.begin([^\n]*)\n(.*?)^struct\.end")


def load_localization() -> tuple[set[str], dict[str, dict[str, str]], list[dict]]:
    result: set[str] = set(); source_entries: dict[str, dict[str, str]] = {}; duplicates: set[str] = set(); missing_languages: list[dict] = []
    for path in localization_files():
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            sid = entry["sid"]
            if sid in result: duplicates.add(sid)
            result.add(sid)

            languages = entry.get("languages", {})
            source_entries[sid] = {str(language): str(text) for language, text in languages.items()}
            missing = [language for language in REQUIRED_LANGUAGES if not str(languages.get(language, "")).strip()]
            if missing:
                missing_languages.append({
                    "sid": sid,
                    "file": path.name,
                    "missing_languages": missing,
                })
    if duplicates: raise ValueError("Duplicate localization SIDs: " + ", ".join(sorted(duplicates)))
    return result, source_entries, missing_languages


def audit_asset_snapshot(localization_sids: set[str], source_entries: dict[str, dict[str, str]]) -> dict:
    if not ASSET_SNAPSHOT.exists():
        return {"available": False, "error_count": 1, "errors": [f"Localization asset snapshot missing: {ASSET_SNAPSHOT}. Run export_localization_asset_snapshot.py in ZoneKit first."]}
    data = json.loads(ASSET_SNAPSHOT.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    asset_sids = [str(entry.get("sid", "")).strip() for entry in entries]
    counts = defaultdict(int)
    for sid in asset_sids:
        if sid: counts[sid] += 1
    duplicates = sorted(sid for sid, count in counts.items() if count > 1)
    asset_set = set(counts)
    missing = sorted(localization_sids - asset_set)
    asset_only = sorted(asset_set - localization_sids)
    content_mismatches = []
    for entry in entries:
        sid = str(entry.get("sid", "")).strip()
        if sid not in source_entries:
            continue
        asset_languages = entry.get("languages")
        if not isinstance(asset_languages, dict):
            content_mismatches.append({"sid": sid, "language": "*", "reason": "snapshot_has_no_structured_languages"})
            continue
        for language in REQUIRED_LANGUAGES:
            expected = source_entries[sid].get(language, "")
            actual = str(asset_languages.get(language, ""))
            if actual != expected:
                content_mismatches.append({
                    "sid": sid,
                    "language": language,
                    "reason": "value_mismatch",
                    "source": expected,
                    "asset": actual,
                })
    errors = []
    if duplicates: errors.append("Duplicate asset SIDs: " + ", ".join(duplicates))
    if missing: errors.append(f"{len(missing)} source localization SIDs are missing from the asset snapshot")
    if content_mismatches: errors.append(f"{len(content_mismatches)} source language values differ from the asset snapshot")
    return {
        "available": True, "asset_entry_count": len(asset_sids), "source_entry_count": len(localization_sids),
        "missing_count": len(missing), "missing_sids": missing,
        "asset_only_count": len(asset_only), "asset_only_sids": asset_only,
        "duplicate_count": len(duplicates), "duplicate_sids": duplicates,
        "content_mismatch_count": len(content_mismatches), "content_mismatches": content_mismatches,
        "error_count": len(errors), "errors": errors,
    }


def effect_asset_sid(cfg_sid: str) -> str: return f"sid_effects_{cfg_sid}_name"


def audit_upgrade_model(model, localization_sids: set[str]) -> dict:
    text_sids: set[str] = set()
    hint_sids: set[str] = set()
    missing: set[str] = set()
    incomplete: list[dict] = []
    for upgrade in model.upgrades:
        fields = (("text", upgrade.text_sid), ("hint", upgrade.hint_sid))
        if str(upgrade.sid).lower().startswith("bprue"):
            absent = [kind for kind, sid in fields if not sid]
            if absent:
                incomplete.append({"upgrade_sid": upgrade.sid, "missing_fields": absent})
        for kind, sid in fields:
            if not sid or not sid.lower().startswith("sid_bprue_"):
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
        "incomplete_upgrade_count": len(incomplete),
        "incomplete_upgrades": incomplete,
    }


def audit_generated_cfg_localization(localization_sids: set[str]) -> dict:
    references: dict[str, set[str]] = defaultdict(set)
    cfg_roots = (
        REPO_ROOT / "GameLite",
        REPO_ROOT / "Armor" / "GameLite",
        REPO_ROOT / "Editions" / "GameLite",
    )
    for root in cfg_roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.cfg")):
            text = path.read_text(encoding="utf-8", errors="replace")
            for match in BPRUE_TEXT_SID_RE.finditer(text):
                references[match.group(0)].add(str(path.relative_to(REPO_ROOT)))
    missing = []
    case_mismatches = []
    by_lower = {sid.lower(): sid for sid in localization_sids}
    for sid, paths in sorted(references.items()):
        if sid in localization_sids:
            continue
        row = {"sid": sid, "files": sorted(paths)}
        canonical = by_lower.get(sid.lower())
        if canonical:
            row["localization_sid"] = canonical
            case_mismatches.append(row)
        else:
            missing.append(row)
    return {
        "referenced_sid_count": len(references),
        "missing_count": len(missing),
        "missing": missing,
        "case_mismatch_count": len(case_mismatches),
        "case_mismatches": case_mismatches,
    }

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
    for effect_root in (DLC_EFFECT_ROOT, EDITION_EFFECT_ROOT):
        for path in sorted(effect_root.glob("*/EffectPrototypes/*BPRUE*.cfg")):
            catalog.update(_parse_effects(path, str(path.relative_to(REPO_ROOT))))
    catalog.update(_parse_effects(VANILLA_UI_PATCH, VANILLA_UI_PATCH.name))
    catalog.update(_parse_effects(ARMOR_EFFECT_PATCH, str(ARMOR_EFFECT_PATCH.relative_to(REPO_ROOT))))
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

    # Armor is an optional module and is not part of build_model(). Validate every
    # visible generated BPRUE Armor effect so missing UI metadata cannot slip through.
    for effect_sid, entry in catalog.items():
        if entry["source"].startswith("Armor/") and effect_sid.startswith("BPRUE_Armor_"):
            if entry["show"] is not False:
                references[effect_sid].add("Armor")

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
    localization_sids, source_entries, missing_languages = load_localization()
    base_model, configs = build_model(apply_layout=False); dlc_models = build_dlc_outputs(base_model, configs); edition_models = build_edition_outputs(base_model, configs)
    models = {"BaseGame": base_model, **dlc_models, **edition_models}
    scopes = {scope: audit_upgrade_model(model, localization_sids) for scope, model in models.items()}
    effects = audit_referenced_effects(models, localization_sids)
    asset_snapshot = audit_asset_snapshot(localization_sids, source_entries)
    generated_cfg = audit_generated_cfg_localization(localization_sids)
    missing_by_sid: dict[str, list[str]] = defaultdict(list)
    for scope, audit in scopes.items():
        for sid in audit["missing_sids"]: missing_by_sid[sid].append(scope)

    report = {
        "localization_sid_count": len(localization_sids),
        "required_languages": list(REQUIRED_LANGUAGES),
        "missing_language_entry_count": len(missing_languages),
        "missing_languages": missing_languages,
        "scopes": scopes,
        "effects": effects,
        "asset_snapshot": asset_snapshot,
        "generated_cfg": generated_cfg,
        "unique_missing_upgrade_sid_count": len(missing_by_sid),
        "missing_upgrade_sids": {sid: affected for sid, affected in sorted(missing_by_sid.items())},
        "error_count": (
            len(missing_languages)
            + len(missing_by_sid)
            + sum(audit["incomplete_upgrade_count"] for audit in scopes.values())
            + effects["error_count"]
            + asset_snapshot["error_count"]
            + generated_cfg["missing_count"]
            + generated_cfg["case_mismatch_count"]
        ),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True); report_path = REPORT_DIR / "localization_audit.json"; report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Localization SIDs: {len(localization_sids)}")
    print(f"Required languages: {', '.join(REQUIRED_LANGUAGES)} | entries missing a required language: {len(missing_languages)}")
    if asset_snapshot["available"]:
        print(f"Localization asset snapshot: asset={asset_snapshot['asset_entry_count']} source={asset_snapshot['source_entry_count']} missing={asset_snapshot['missing_count']} asset-only={asset_snapshot['asset_only_count']} duplicates={asset_snapshot['duplicate_count']} content-mismatch={asset_snapshot['content_mismatch_count']}")
        for sid in asset_snapshot["missing_sids"]:
            print(f"  MISSING FROM ASSET: {sid}")
        for sid in asset_snapshot["asset_only_sids"]:
            print(f"  STALE ASSET-ONLY SID: {sid}")
        for item in asset_snapshot["content_mismatches"]:
            print(f"  ASSET CONTENT MISMATCH: {item['sid']} [{item['language']}] ({item['reason']})")
    else:
        for error in asset_snapshot["errors"]:
            print(f"  ASSET SNAPSHOT ERROR: {error}")
    for item in missing_languages:
        print(f"  MISSING {', '.join(item['missing_languages'])}: {item['sid']} ({item['file']})")
    for scope, audit in scopes.items(): print(f"{scope}: upgrades={audit['upgrade_count']} text={audit['text_sid_count']} hints={audit['hint_sid_count']} missing={audit['missing_count']}")
    print(f"Effects: referenced={effects['referenced_effect_count']} visible={effects['visible_effect_count']} vanilla-localized={effects['vanilla_localization_count']} errors={effects['error_count']}")
    print(f"Total localization errors: {report['error_count']}")
    print(f"Report: {report_path}")
    if report["error_count"]: raise SystemExit(1)


if __name__ == "__main__": main()
