from __future__ import annotations

import json
import re
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PYTHON_ROOT.parent
LOCALIZATION_DIR = Path(__file__).resolve().parent
CFG_GENERATORS = PYTHON_ROOT / "CFGGenerators"

LOCALIZATION_FILES = (
    LOCALIZATION_DIR / "Blueprint_Localization.json",
    LOCALIZATION_DIR / "Weapon_Module_Localization.json",
    LOCALIZATION_DIR / "Shared_Specialization_Localization.json",
    LOCALIZATION_DIR / "Stock_Localization.json",
    LOCALIZATION_DIR / "Effect_Localization.json",
)

EFFECT_SID_RE = re.compile(r"^\s*LocalizationSID\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)
UPGRADE_TEXT_RE = re.compile(r"^\s*(?:Text|Hint)\s*=\s*([A-Za-z0-9_]+)\s*$", re.MULTILINE)
VISIBLE_RE = re.compile(r"^\s*ShowUpgradeEffect\s*=\s*true\s*$", re.MULTILINE | re.IGNORECASE)
PROTOTYPE_RE = re.compile(r"(?ms)^([A-Za-z0-9_]+)\s*:\s*struct\.begin[^\n]*\n(.*?)^struct\.end")


def load_localization_sids() -> set[str]:
    result=set(); duplicates=set()
    for path in LOCALIZATION_FILES:
        data=json.loads(path.read_text(encoding="utf-8"))
        for entry in data.get("entries",[]):
            sid=entry["sid"]
            if sid in result: duplicates.add(sid)
            result.add(sid)
    if duplicates: raise ValueError("Duplicate localization SIDs: "+", ".join(sorted(duplicates)))
    return result


def effect_asset_sid(cfg_sid: str) -> str: return f"sid_effects_{cfg_sid}_name"


def main() -> None:
    localization_sids=load_localization_sids(); errors=[]
    upgrade_cfg=REPO_ROOT/"GameLite/ModGameData/BPRUpgradesExpanded/UpgradePrototypes/BPRUE_UpgradePrototypes.cfg"
    if upgrade_cfg.exists():
        for sid in sorted(set(UPGRADE_TEXT_RE.findall(upgrade_cfg.read_text(encoding="utf-8")))):
            if sid.startswith("sid_bprue_") and sid not in localization_sids: errors.append(f"missing upgrade localization: {sid}")
    effect_dir=REPO_ROOT/"GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes"
    for path in sorted(effect_dir.glob("BPRUE_*EffectPrototypes.cfg")):
        text=path.read_text(encoding="utf-8")
        for prototype_sid,body in PROTOTYPE_RE.findall(text):
            if not prototype_sid.startswith("BPRUE_") or not VISIBLE_RE.search(body): continue
            match=EFFECT_SID_RE.search(body)
            if not match: errors.append(f"{path.name}:{prototype_sid}: visible effect has no LocalizationSID"); continue
            asset_sid=effect_asset_sid(match.group(1))
            if asset_sid not in localization_sids: errors.append(f"{path.name}:{prototype_sid}: missing localization {asset_sid}")
    if errors: raise ValueError("Localization validation failed:\n  - "+"\n  - ".join(errors))
    print(f"Localization validation successful ({len(localization_sids)} SIDs indexed).")

if __name__ == "__main__": main()
