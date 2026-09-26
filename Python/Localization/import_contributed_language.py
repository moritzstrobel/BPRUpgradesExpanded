from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def load_entries_from_zip(zip_path: Path) -> dict[str, dict]:
    result = {}
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.endswith("_Localization.json"):
                continue
            data = json.loads(archive.read(name).decode("utf-8"))
            for entry in data.get("entries", []):
                sid = str(entry.get("sid", "")).strip()
                if sid:
                    result[sid] = entry
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge one contributed language into current BPRUE localization sources by SID.")
    parser.add_argument("zip", type=Path, help="Contributor localization ZIP")
    parser.add_argument("--language", default="Chinese")
    parser.add_argument("--write", action="store_true", help="Write matching translations into the current JSON sources")
    args = parser.parse_args()

    contributed = load_entries_from_zip(args.zip)
    current_files = sorted(SCRIPT_DIR.glob("*_Localization.json"))
    current_sids = set()
    translated = []
    missing_translation = []
    contributor_only = []

    for path in current_files:
        data = json.loads(path.read_text(encoding="utf-8"))
        changed = False
        for entry in data.get("entries", []):
            sid = str(entry.get("sid", "")).strip()
            if not sid:
                continue
            current_sids.add(sid)
            source = contributed.get(sid, {})
            value = str(source.get("languages", {}).get(args.language, "")).strip()
            if value:
                if entry.setdefault("languages", {}).get(args.language) != value:
                    entry["languages"][args.language] = value
                    changed = True
                translated.append(sid)
            else:
                missing_translation.append(sid)
        if args.write and changed:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    contributor_only = sorted(set(contributed) - current_sids)
    translated = sorted(set(translated))
    missing_translation = sorted(set(missing_translation))

    print(f"Language: {args.language}")
    print(f"Current SIDs: {len(current_sids)}")
    print(f"Contributor SIDs: {len(contributed)}")
    print(f"Matched translations: {len(translated)}")
    print(f"Current SIDs missing {args.language}: {len(missing_translation)}")
    for sid in missing_translation:
        print(f"  MISSING {args.language}: {sid}")
    print(f"Contributor-only/stale SIDs: {len(contributor_only)}")
    for sid in contributor_only:
        print(f"  CONTRIBUTOR ONLY: {sid}")
    if not args.write:
        print("Dry run only. Re-run with --write to merge matching translations.")


if __name__ == "__main__":
    main()
