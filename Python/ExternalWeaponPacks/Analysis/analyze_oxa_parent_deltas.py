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
ATTACH = re.compile(r"(?m)^\s*AttachPrototypeSID\s*=\s*([^\s/]+)")
FIT_ARRAY = re.compile(r"(?ms)^\s*FittingWeaponsSIDs\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*(.*?)^\s*struct\.end")
INDEXED = re.compile(r"(?m)^\s*\[\d+\]\s*=\s*([^\s/]+)")


def blocks(text: str):
    text = text.lstrip("\ufeff")
    matches = list(TOP.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield match.group(1), text[match.start():end]


def cfg_files(root: Path):
    return sorted(root.rglob("*.cfg")) if root.exists() else []


def setup_attachments(root: Path, setup_sid: str) -> set[str]:
    result = set()
    for path in cfg_files(root):
        if "WeaponGeneralSetupPrototypes" not in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for sid, block in blocks(text):
            if sid == setup_sid:
                result.update(ATTACH.findall(block))
    return result


def fitting_attachments(root: Path, weapon_sid: str) -> set[str]:
    result = set()
    for path in cfg_files(root):
        if "ItemPrototypes" not in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for attach_sid, block in blocks(text):
            for body in FIT_ARRAY.findall(block):
                if weapon_sid in INDEXED.findall(body):
                    result.add(attach_sid)
    return result


def source_weapon_sid(source_setup: str) -> str:
    if source_setup == "GunArev_ST_GS":
        return "GunArev_ST"
    return source_setup


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = []
    lines = ["OXA pseudo-parent attachment delta", "==================================", ""]
    seen = set()
    for pack_name, pack in registry["packs"].items():
        lines += [pack_name, "=" * len(pack_name)]
        for weapon in pack["weapons"]:
            source_setup = weapon["oxa_source_setup"]
            key = (pack_name, source_setup)
            if key not in seen:
                seen.add(key)
                source_weapon = source_weapon_sid(source_setup)
                vanilla_setup = setup_attachments(VANILLA_ROOT, source_setup)
                oxa_setup = setup_attachments(OXA_ROOT, source_setup)
                vanilla_fit = fitting_attachments(VANILLA_ROOT, source_weapon)
                oxa_fit = fitting_attachments(OXA_ROOT, source_weapon)
                row = {
                    "pack": pack_name,
                    "source_setup": source_setup,
                    "source_weapon": source_weapon,
                    "vanilla_compatible_attachments": sorted(vanilla_setup),
                    "oxa_compatible_attachments": sorted(oxa_setup),
                    "oxa_setup_delta": sorted(oxa_setup - vanilla_setup),
                    "vanilla_fitting_attachments": sorted(vanilla_fit),
                    "oxa_fitting_attachments": sorted(oxa_fit),
                    "oxa_fitting_delta": sorted(oxa_fit - vanilla_fit),
                }
                rows.append(row)
                lines += [
                    f"Pseudo parent: {source_setup} ({source_weapon})",
                    f"  Vanilla CompatibleAttachments: {len(vanilla_setup)}",
                    f"  OXA CompatibleAttachments: {len(oxa_setup)}",
                    f"  OXA setup delta: {len(row['oxa_setup_delta'])}",
                    f"  Vanilla fitting attachments: {len(vanilla_fit)}",
                    f"  OXA fitting attachments: {len(oxa_fit)}",
                    f"  OXA fitting delta: {len(row['oxa_fitting_delta'])}",
                ]
                if row["oxa_setup_delta"]:
                    lines.append("  setup delta SIDs:")
                    lines.extend(f"    + {sid}" for sid in row["oxa_setup_delta"])
                if row["oxa_fitting_delta"]:
                    lines.append("  fitting delta SIDs:")
                    lines.extend(f"    + {sid}" for sid in row["oxa_fitting_delta"])
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
