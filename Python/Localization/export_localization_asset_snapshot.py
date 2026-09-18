import json
import os
import unreal

ASSET_PATH = "/BPRUpgradesExpanded/Localization/L_BPRUpgradesExpanded"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.normpath(
    os.path.join(SCRIPT_DIR, "..", "Analysis", "Reports", "localization_asset_snapshot.json")
)

def log(message):
    unreal.log(f"[BlueprintLocalizationSnapshot] {message}")

def get_sid(entry):
    return str(entry.get_editor_property("SID"))

def export_languages(entry):
    # ExportText gives us the complete struct representation without depending
    # on the concrete Python wrapper type of LanguagesToLocalizedStrings.
    text = entry.export_text()
    return text

asset = unreal.load_asset(ASSET_PATH)
if asset is None:
    raise RuntimeError(f"Could not load localization asset: {ASSET_PATH}")

localized_texts = asset.get_editor_property("LocalizedTexts")
entries = []
seen = set()
for entry in localized_texts:
    sid = get_sid(entry)
    if sid in seen:
        raise RuntimeError(f"Duplicate SID in localization asset: {sid}")
    seen.add(sid)
    entries.append({"sid": sid, "export_text": export_languages(entry)})

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
with open(REPORT_PATH, "w", encoding="utf-8") as handle:
    json.dump(
        {"asset_path": ASSET_PATH, "entry_count": len(entries), "entries": entries},
        handle,
        ensure_ascii=False,
        indent=2,
    )
    handle.write("\n")

log(f"Exported {len(entries)} entries to {REPORT_PATH}")
