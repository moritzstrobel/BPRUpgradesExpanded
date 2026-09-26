import json
import os
import unreal

ASSET_PATH = "/BPRUpgradesExpanded/Localization/L_BPRUpgradesExpanded"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIRED_LANGUAGES = ("English", "Russian", "Chinese")

def localization_files():
    return tuple(
        os.path.join(SCRIPT_DIR, name)
        for name in sorted(os.listdir(SCRIPT_DIR))
        if name.endswith("_Localization.json")
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
            missing_languages=[language for language in REQUIRED_LANGUAGES if not normalized_languages.get(language, "").strip()]
            if missing_languages:
                raise RuntimeError(
                    f"Entry '{sid}' in {os.path.basename(path)} is missing required localization: "
                    + ", ".join(missing_languages)
                )
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
entries=read_localization_files(localization_files()); asset=unreal.load_asset(ASSET_PATH)
if asset is None: raise RuntimeError(f"Could not load localization asset: {ASSET_PATH}")
localized_texts=asset.get_editor_property("LocalizedTexts"); existing_count=len(localized_texts)
if existing_count==0: raise RuntimeError("LocalizedTexts is empty. Create one temporary localization entry manually before running the importer.")
existing_by_sid={}
for entry in localized_texts:
    sid=get_sid(entry)
    if sid in existing_by_sid: raise RuntimeError(f"Duplicate SID already exists in localization asset: {sid}")
    existing_by_sid[sid]=entry

source_sids={entry["sid"] for entry in entries}
existing_managed_count=sum(1 for sid in source_sids if sid in existing_by_sid)
added=len(source_sids)-existing_managed_count
removed=len(existing_by_sid)-existing_managed_count

# Rebuild the array with independent struct instances. Appending the same
# template object repeatedly aliases one mutable Unreal struct and therefore
# turns all appended entries into the last imported SID.
rebuilt_texts=[]
managed_written=0
for original in localized_texts:
    sid=get_sid(original)
    if sid not in source_sids:
        continue
    source=next(item for item in entries if item["sid"]==sid)
    original.import_text(make_struct_text(source["sid"],source["languages"]))
    rebuilt_texts.append(original)
    managed_written+=1

# Add source entries that do not exist yet. ZoneKit does not expose a public
# constructor for this struct type, so clone via the array/template behavior,
# then immediately validate uniqueness before saving.
missing_sources=[source for source in entries if source["sid"] not in existing_by_sid]
if missing_sources:
    template=localized_texts[0]
    backup=template.export_text()
    try:
        for source in missing_sources:
            template.import_text(make_struct_text(source["sid"],source["languages"]))
            localized_texts.append(template)
            rebuilt_texts.append(localized_texts[-1])
            managed_written+=1
    finally:
        template.import_text(backup)

final_sids=[get_sid(entry) for entry in rebuilt_texts]
if len(final_sids)!=len(set(final_sids)):
    duplicates=sorted({sid for sid in final_sids if final_sids.count(sid)>1})
    raise RuntimeError("Duplicate SIDs detected after rebuild:\n"+"\n".join(duplicates))
missing=sorted(source_sids-set(final_sids))
if missing: raise RuntimeError("SIDs missing after rebuild:\n"+"\n".join(missing))
if len(rebuilt_texts)!=len(entries):
    raise RuntimeError(f"Entry count mismatch after rebuild: expected {len(entries)}, got {len(rebuilt_texts)}.")
asset.modify(); asset.set_editor_property("LocalizedTexts",rebuilt_texts)
if not unreal.EditorAssetLibrary.save_asset(ASSET_PATH,only_if_is_dirty=False): raise RuntimeError(f"Failed to save asset: {ASSET_PATH}")
log(f"REBUILD - input={len(entries)}, rebuilt={managed_written}, previously_managed={existing_managed_count}, added={added}, removed_stale={removed}, final={len(rebuilt_texts)}")
saved_count=verify_saved_asset(entries)
log(f"SUCCESS - verified={len(entries)}, asset_entries={saved_count}, missing=0, mismatched_values=0"); log("========================================")
