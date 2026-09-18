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

def language_name(language):
    raw = str(language)
    if "LocalizationLanguage." in raw:
        raw = raw.split("LocalizationLanguage.", 1)[1].split(":", 1)[0].split(">", 1)[0]
    return raw.strip().replace("_", " ").title().replace(" ", "")

def export_languages(entry):
    value = entry.get_editor_property("LanguagesToLocalizedStrings")
    result = {}
    if hasattr(value, "items"):
        for language, text in value.items():
            result[language_name(language)] = str(text)
        return result
    raise RuntimeError(
        "LanguagesToLocalizedStrings is not exposed as a mapping by ZoneKit Python "
        f"(type={type(value).__name__})."
    )

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
    entries.append({"sid": sid, "languages": export_languages(entry)})

os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
with open(REPORT_PATH, "w", encoding="utf-8") as handle:
    json.dump(
        {"asset_path": ASSET_PATH, "entry_count": len(entries), "entries": entries},
        handle,
        ensure_ascii=False,
        indent=2,
    )
    handle.write("\n")

log(f"Exported {len(entries)} entries with structured languages to {REPORT_PATH}")
