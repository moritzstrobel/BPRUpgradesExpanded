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

def language_name(language):
    raw=str(language)
    if "LocalizationLanguage." in raw:
        raw=raw.split("LocalizationLanguage.",1)[1].split(":",1)[0].split(">",1)[0]
    return raw.strip().replace("_"," ").title().replace(" ","")

def get_languages(entry):
    value=entry.get_editor_property("LanguagesToLocalizedStrings")
    if not hasattr(value,"items"):
        raise RuntimeError(
            "LanguagesToLocalizedStrings is not exposed as a mapping by ZoneKit Python "
            f"(type={type(value).__name__})."
        )
    return {language_name(language):str(text) for language,text in value.items()}

def verify_saved_asset(source_entries):
    # ZoneKit does not expose EditorAssetLibrary.unload_asset(). Verify the
    # post-save asset state through a fresh load request instead. The separate
    # snapshot exporter remains the independent disk/audit verification step.
    saved_asset=unreal.load_asset(ASSET_PATH)
    if saved_asset is None:
        raise RuntimeError(f"Could not load saved localization asset for verification: {ASSET_PATH}")
    saved_texts=saved_asset.get_editor_property("LocalizedTexts")
    saved_by_sid={}
    duplicates=[]
    for saved_entry in saved_texts:
        sid=get_sid(saved_entry)
        if sid in saved_by_sid:
            duplicates.append(sid)
        saved_by_sid[sid]=saved_entry
    if duplicates:
        raise RuntimeError("Duplicate SIDs detected after save/reload:\n"+"\n".join(sorted(set(duplicates))))

    missing=[]
    mismatches=[]
    for source in source_entries:
        sid=source["sid"]
        saved_entry=saved_by_sid.get(sid)
        if saved_entry is None:
            missing.append(sid)
            continue
        actual_languages=get_languages(saved_entry)
        for language,expected in source["languages"].items():
            actual=actual_languages.get(language)
            if actual != expected:
                mismatches.append({
                    "sid":sid,
                    "language":language,
                    "expected":expected,
                    "actual":actual,
                })

    log("VERIFY AFTER SAVE (loaded asset state)")
    log(f"verified={len(source_entries)-len(missing)}, missing={len(missing)}, mismatched_values={len(mismatches)}")
    for sid in missing:
        log(f"VERIFY MISSING SID: {sid}")
    for mismatch in mismatches:
        actual="<missing>" if mismatch["actual"] is None else mismatch["actual"]
        log(f"VERIFY MISMATCH: {mismatch['sid']} [{mismatch['language']}]")
        log(f"  expected: {mismatch['expected']}")
        log(f"  actual:   {actual}")
    if missing or mismatches:
        raise RuntimeError(
            f"Localization verification failed after save/reload: "
            f"missing={len(missing)}, mismatched_values={len(mismatches)}"
        )
    return len(saved_texts)

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

source_sids={entry["sid"] for entry in entries}
unmanaged_exports=[entry.export_text() for entry in localized_texts if get_sid(entry) not in source_sids]
existing_managed_count=sum(1 for sid in source_sids if sid in existing_by_sid)
added=len(source_sids)-existing_managed_count

# Rebuild every source-managed struct from the JSON source of truth. Reusing the
# existing structs left stale language-map members behind in ZoneKit.
template=localized_texts[0]
template_backup=template.export_text()
rebuilt_exports=[]
try:
    for source in entries:
        template.import_text(make_struct_text(source["sid"],source["languages"]))
        rebuilt_exports.append(template.export_text())
finally:
    template.import_text(template_backup)

# Reconstruct the complete array from serialized struct values. Asset-only
# entries remain byte-for-byte equivalent at the struct export level; managed
# entries are recreated entirely from the JSON sources.
all_exports=unmanaged_exports+rebuilt_exports
rebuilt_texts=[]
template=localized_texts[0]
template_backup=template.export_text()
try:
    for struct_text in all_exports:
        template.import_text(struct_text)
        rebuilt_texts.append(template)
finally:
    template.import_text(template_backup)

final_sids=[get_sid(entry) for entry in rebuilt_texts]
if len(final_sids)!=len(set(final_sids)): raise RuntimeError("Duplicate SIDs detected after rebuild.")
missing=sorted(source_sids-set(final_sids))
if missing: raise RuntimeError("SIDs missing after rebuild:\n"+"\n".join(missing))
if len(rebuilt_texts)!=len(unmanaged_exports)+len(entries):
    raise RuntimeError("Entry count mismatch after rebuild.")
asset.modify(); asset.set_editor_property("LocalizedTexts",rebuilt_texts)
if not unreal.EditorAssetLibrary.save_asset(ASSET_PATH,only_if_is_dirty=False): raise RuntimeError(f"Failed to save asset: {ASSET_PATH}")
log(f"REBUILD - input={len(entries)}, rebuilt={len(entries)}, previously_managed={existing_managed_count}, added={added}, preserved_unmanaged={len(unmanaged_exports)}, final={len(rebuilt_texts)}")
saved_count=verify_saved_asset(entries)
log(f"SUCCESS - verified={len(entries)}, asset_entries={saved_count}, missing=0, mismatched_values=0"); log("========================================")
