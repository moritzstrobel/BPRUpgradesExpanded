from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "Python/ExternalWeaponPacks/weapon_packs.json"
OXA_ROOT = ROOT / "Python/VanillaReference/OxaData"
VANILLA_ROOT = ROOT / "Python/VanillaReference"
OUT_TXT = ROOT / "Python/ExternalWeaponPacks/Reports/oxa_parent_deltas.txt"
OUT_JSON = ROOT / "Python/ExternalWeaponPacks/Reports/oxa_parent_deltas.json"

TOP = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?")
ATTACH_BLOCK = re.compile(r"(?ms)^\s*\[\d+\]\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*(.*?)^\s*struct\.end")
ATTACH_SID = re.compile(r"(?m)^\s*AttachPrototypeSID\s*=\s*([^\s/]+)")
FIT_ARRAY = re.compile(r"(?ms)^\s*FittingWeaponsSIDs\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*(.*?)^\s*struct\.end")
INDEXED = re.compile(r"(?m)^\s*\[\d+\]\s*=\s*([^\s/]+)")
SCALAR = re.compile(r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$")


def blocks(text: str):
    text = text.lstrip("\ufeff")
    matches = list(TOP.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield match.group(1), text[match.start():end]


def cfg_files(root: Path):
    return sorted(root.rglob("*.cfg")) if root.exists() else []


def normalized_entry(body: str) -> dict:
    fields = {}
    for key, value in SCALAR.findall(body):
        value = value.split("//", 1)[0].strip()
        if value:
            fields[key] = value
    # Preserve nested requirement/list values as normalized SID lists.
    for name in ("RequiredUpgradeIDs", "RequiredAttachPrototypeSIDs"):
        match = re.search(
            rf"(?ms)^\s*{name}\s*:\s*struct\.begin(?:\s*\{{[^}}]*\}})?\s*(.*?)^\s*struct\.end",
            body,
        )
        if match:
            fields[name] = sorted(INDEXED.findall(match.group(1)))
    return fields


def setup_entries(root: Path, setup_sid: str) -> dict[str, dict]:
    result = {}
    for path in cfg_files(root):
        if "WeaponGeneralSetupPrototypes" not in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for sid, block in blocks(text):
            if sid != setup_sid:
                continue
            match = re.search(
                r"(?ms)^\s*CompatibleAttachments\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*(.*?)^\s*struct\.end",
                block,
            )
            if not match:
                continue
            for body in ATTACH_BLOCK.findall(match.group(1)):
                sid_match = ATTACH_SID.search(body)
                if sid_match:
                    result[sid_match.group(1)] = normalized_entry(body)
    return result


def fitting_entries(root: Path, weapon_sid: str) -> dict[str, list[str]]:
    result = {}
    for path in cfg_files(root):
        if "ItemPrototypes" not in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for attach_sid, block in blocks(text):
            values = set()
            for body in FIT_ARRAY.findall(block):
                values.update(INDEXED.findall(body))
            if weapon_sid in values:
                result[attach_sid] = sorted(values)
    return result


def structural_diff(vanilla: dict, oxa: dict) -> dict:
    vk, ok = set(vanilla), set(oxa)
    common = vk & ok
    return {
        "added": sorted(ok - vk),
        "removed": sorted(vk - ok),
        "modified": sorted(key for key in common if vanilla[key] != oxa[key]),
        "unchanged": sorted(key for key in common if vanilla[key] == oxa[key]),
    }


def source_weapon_sid(source_setup: str) -> str:
    return "GunArev_ST" if source_setup == "GunArev_ST_GS" else source_setup


def changed_fields(before: dict, after: dict) -> dict:
    keys = sorted(set(before) | set(after))
    return {
        key: {"vanilla": before.get(key), "oxa": after.get(key)}
        for key in keys if before.get(key) != after.get(key)
    }


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows, lines, seen = [], ["OXA pseudo-parent structural attachment diff", "============================================", ""], set()
    for pack_name, pack in registry["packs"].items():
        lines += [pack_name, "=" * len(pack_name)]
        for weapon in pack["weapons"]:
            source_setup = weapon["oxa_source_setup"]
            key = (pack_name, source_setup)
            if key in seen:
                continue
            seen.add(key)
            source_weapon = source_weapon_sid(source_setup)
            vanilla_setup, oxa_setup = setup_entries(VANILLA_ROOT, source_setup), setup_entries(OXA_ROOT, source_setup)
            vanilla_fit, oxa_fit = fitting_entries(VANILLA_ROOT, source_weapon), fitting_entries(OXA_ROOT, source_weapon)
            setup_diff, fit_diff = structural_diff(vanilla_setup, oxa_setup), structural_diff(vanilla_fit, oxa_fit)
            setup_changes = {
                sid: changed_fields(vanilla_setup[sid], oxa_setup[sid])
                for sid in setup_diff["modified"]
            }
            fit_changes = {
                sid: {"vanilla": vanilla_fit[sid], "oxa": oxa_fit[sid]}
                for sid in fit_diff["modified"]
            }
            row = {
                "pack": pack_name, "source_setup": source_setup, "source_weapon": source_weapon,
                "compatible_attachments": {
                    "vanilla_count": len(vanilla_setup), "oxa_count": len(oxa_setup),
                    **setup_diff, "modified_fields": setup_changes,
                },
                "fitting_weapons": {
                    "vanilla_count": len(vanilla_fit), "oxa_count": len(oxa_fit),
                    **fit_diff, "modified_memberships": fit_changes,
                },
            }
            rows.append(row)
            lines += [
                f"Pseudo parent: {source_setup} ({source_weapon})",
                f"  CompatibleAttachments: Vanilla={len(vanilla_setup)}, OXA={len(oxa_setup)}",
                f"    added={len(setup_diff['added'])}, removed={len(setup_diff['removed'])}, modified={len(setup_diff['modified'])}, unchanged={len(setup_diff['unchanged'])}",
                f"  FittingWeaponsSIDs: Vanilla={len(vanilla_fit)}, OXA={len(oxa_fit)}",
                f"    added={len(fit_diff['added'])}, removed={len(fit_diff['removed'])}, modified={len(fit_diff['modified'])}, unchanged={len(fit_diff['unchanged'])}",
            ]
            for label in ("added", "removed", "modified"):
                if setup_diff[label]:
                    lines.append(f"  CompatibleAttachments {label}:")
                    for sid in setup_diff[label]:
                        lines.append(f"    {sid}")
                        if label == "modified":
                            for field, values in setup_changes[sid].items():
                                lines.append(f"      {field}: {values['vanilla']} -> {values['oxa']}")
            for label in ("added", "removed", "modified"):
                if fit_diff[label]:
                    lines.append(f"  FittingWeaponsSIDs {label}:")
                    for sid in fit_diff[label]:
                        lines.append(f"    {sid}")
                        if label == "modified":
                            lines.append(f"      Vanilla: {', '.join(fit_changes[sid]['vanilla'])}")
                            lines.append(f"      OXA: {', '.join(fit_changes[sid]['oxa'])}")
            lines.append("")
        lines.append("")
    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"pseudo_parents": rows}, indent=2), encoding="utf-8")
    print(OUT_TXT.read_text(encoding="utf-8"), end="")
    print(f"Text report: {OUT_TXT.relative_to(ROOT).as_posix()}")
    print(f"JSON report: {OUT_JSON.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
