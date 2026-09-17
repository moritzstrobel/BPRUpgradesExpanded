import json
import os
import unreal

ASSET_PATH = "/BPRUpgradesExpanded/Localization/L_BPRUpgradesExpanded"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALIZATION_FILES = (
    os.path.join(SCRIPT_DIR, "Blueprint_Localization.json"),
    os.path.join(SCRIPT_DIR, "Conversion_Localization.json"),
    os.path.join(SCRIPT_DIR, "Weapon_Module_Localization.json"),
    os.path.join(SCRIPT_DIR, "Kora_Localization.json"),
    os.path.join(SCRIPT_DIR, "MachineGun_Localization.json"),
    os.path.join(SCRIPT_DIR, "Shared_Specialization_Localization.json"),
    os.path.join(SCRIPT_DIR, "Stock_Localization.json"),
    os.path.join(SCRIPT_DIR, "Effect_Localization.json"),
    os.path.join(SCRIPT_DIR, "Unique_Localization.json"),
    os.path.join(SCRIPT_DIR, "Unique_Sniper_Localization.json"),
    os.path.join(SCRIPT_DIR, "Unique_MachineGun_Localization.json"),
    os.path.join(SCRIPT_DIR, "DLC1_Localization.json"),
)

def log(message): unreal.log(f"[BlueprintLocalization] {message}")
def escape_unreal_string(value): return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "\\n")

def read_localization_files(paths):
    normalized=[]; seen=set()
    for path in paths:
        if not os.path.isfile(path): raise RuntimeError(f"Localization file does not exist:\n{path}")
        with open(path,"r",encoding="utf-8") as file: entries=json.load(file).get("entries")
        if not isinstance(entries,list): raise RuntimeError(f"Localization JSON must contain an 'entries' array: {path}")
        for index,entry in enumerate(entries,start=1):
            if not isinstance(entry,dict): raise RuntimeError(f"Entry #{index} in {path} is not an object.")
            sid=str(entry.get("sid","")).strip(); languages=entry.get("languages")
            if not sid: raise RuntimeError(f"Entry #{index} in {path} has an empty SID.")
            if sid in seen: raise RuntimeError(f"Duplicate localization SID across sources: {sid}")
            if not isinstance(languages,dict) or not languages: raise RuntimeError(f"Entry '{sid}' has no valid languages object.")
            normalized_languages={str(language).strip():str(text) for language,text in languages.items() if str(language).strip()}
            if len(normalized_languages)!=len(languages): raise RuntimeError(f"Entry '{sid}' contains an empty language key.")
            normalized.append({"sid":sid,"languages":normalized_languages}); seen.add(sid)
        log(f"Read {len(entries)} entries from {os.path.basename(path)}")
    return normalized

def make_struct_text(sid,languages):
    parts=[f'({language}, "{escape_unreal_string(text)}")' for language,text in languages.items()]
    return f'(SID="{escape_unreal_string(sid)}",LanguagesToLocalizedStrings=({",".join(parts)}))'
def get_sid(entry): return str(entry.get_editor_property("SID"))

def main():
    asset=unreal.load_asset(ASSET_PATH)
    if not asset: raise RuntimeError(f"Could not load localization asset: {ASSET_PATH}")
    desired=read_localization_files(LOCALIZATION_FILES); desired_by_sid={entry["sid"]:entry for entry in desired}
    current=list(asset.get_editor_property("LocalizationData")); current_by_sid={get_sid(entry):entry for entry in current}
    result=[]; added=updated=unchanged=0
    for entry in desired:
        sid=entry["sid"]; struct_text=make_struct_text(sid,entry["languages"])
        parsed=unreal.LocalizationData()
        if not parsed.import_text(struct_text): raise RuntimeError(f"Could not import localization entry: {sid}")
        existing=current_by_sid.get(sid)
        if existing is None: added+=1
        elif existing.export_text()!=parsed.export_text(): updated+=1
        else: unchanged+=1
        result.append(parsed)
    preserved=[entry for entry in current if get_sid(entry) not in desired_by_sid]
    result.extend(preserved)
    asset.set_editor_property("LocalizationData",result); unreal.EditorAssetLibrary.save_loaded_asset(asset)
    log(f"Localization upsert complete: desired={len(desired)}, added={added}, updated={updated}, unchanged={unchanged}, preserved={len(preserved)}")

if __name__ == "__main__": main()
