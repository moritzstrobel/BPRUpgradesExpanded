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

log("========================================"); log("Starting localization UPSERT")
entries=read_localization_files(LOCALIZATION_FILES); asset=unreal.load_asset(ASSET_PATH)
if asset is None: raise RuntimeError(f"Could not load localization asset: {ASSET_PATH}")
localized_texts=asset.get_editor_property("LocalizedTexts"); existing_count=len(localized_texts)
if existing_count==0: raise RuntimeError("LocalizedTexts is empty. Create one temporary localization entry manually before running the importer.")
existing_by_sid={}
for entry in localized_texts:
    sid=get_sid(entry)
    if sid in existing_by_sid: raise RuntimeError(f"Duplicate SID already exists in localization asset: {sid}")
    existing_by_sid[sid]=entry
updated=0; to_add=[]
for entry in entries:
    existing=existing_by_sid.get(entry["sid"])
    if existing is None: to_add.append(entry)
    else: existing.import_text(make_struct_text(entry["sid"],entry["languages"])); updated+=1
added=0
if to_add:
    template=localized_texts[0]; backup=template.export_text()
    try:
        for entry in to_add: template.import_text(make_struct_text(entry["sid"],entry["languages"])); localized_texts.append(template); added+=1
    finally: template.import_text(backup)
final_sids=[get_sid(entry) for entry in localized_texts]
if len(final_sids)!=len(set(final_sids)): raise RuntimeError("Duplicate SIDs detected after UPSERT.")
missing=sorted({entry['sid'] for entry in entries}-set(final_sids))
if missing: raise RuntimeError("SIDs missing after UPSERT:\n"+"\n".join(missing))
if len(localized_texts)!=existing_count+added: raise RuntimeError("Entry count mismatch after UPSERT.")
asset.modify(); asset.set_editor_property("LocalizedTexts",localized_texts)
if not unreal.EditorAssetLibrary.save_asset(ASSET_PATH,only_if_is_dirty=False): raise RuntimeError(f"Failed to save asset: {ASSET_PATH}")
log(f"SUCCESS - input={len(entries)}, updated={updated}, added={added}, final={len(localized_texts)}"); log("========================================")
