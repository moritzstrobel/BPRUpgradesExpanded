from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VANILLA_ROOT = ROOT / "Python/VanillaReference"
DEFAULT_PACKS = {
    "MK17": DEFAULT_VANILLA_ROOT / "MK17Data",
    "ModernAK": DEFAULT_VANILLA_ROOT / "ModernAKData",
}
DEFAULT_TEXT_OUT = ROOT / "Python/ExternalWeaponPacks/Reports/weapon_packs.txt"
DEFAULT_JSON_OUT = ROOT / "Python/ExternalWeaponPacks/Reports/weapon_packs.json"

TOP_LEVEL = re.compile(
    r"(?m)^\s*([A-Za-z0-9_]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?"
)
SCALAR = re.compile(r"(?m)^\s*{name}\s*=\s*([^\s/]+)")
ARRAY = re.compile(
    r"(?ms)^\s*{name}\s*:\s*struct\.begin(?:\s*\{{[^}}]*\}})?\s*(.*?)^\s*struct\.end"
)
INDEXED = re.compile(r"(?m)^\s*\[(\d+)\]\s*=\s*([^\s/]+)")


def _game_data_roots(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.name == "GameData":
        return [root]
    return sorted(path for path in root.rglob("GameData") if path.is_dir())


def _matching_files(game_data: Path, fragment: str) -> list[Path]:
    return sorted(
        path for path in game_data.rglob("*.cfg")
        if fragment.lower() in path.as_posix().lower()
    )


def _top_level_blocks(text: str):
    matches = list(TOP_LEVEL.finditer(text))
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield match.group(1), match.group(2) or "", text[start:end]


def _scalar(block: str, name: str) -> str | None:
    match = re.search(SCALAR.pattern.format(name=re.escape(name)), block)
    return match.group(1) if match else None


def _array(block: str, name: str) -> list[str]:
    match = re.search(ARRAY.pattern.format(name=re.escape(name)), block)
    if not match:
        return []
    indexed = [(int(i), value) for i, value in INDEXED.findall(match.group(1))]
    return [value for _, value in sorted(indexed)]


def _refkey(modes: str) -> str | None:
    match = re.search(r"(?:^|;)\s*refkey\s*=\s*([^;}]+)", modes)
    return match.group(1).strip() if match else None


def _collect_family(game_data: Path, fragment: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in _matching_files(game_data, fragment):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for sid, modes, block in _top_level_blocks(text):
            entry = result.setdefault(sid, {
                "sid": sid,
                "sources": [],
                "refkeys": [],
                "fields": {},
            })
            entry["sources"].append(path.relative_to(game_data).as_posix())
            refkey = _refkey(modes)
            if refkey and refkey not in entry["refkeys"]:
                entry["refkeys"].append(refkey)
            for field in (
                "SID", "GeneralWeaponSetup", "PlayerWeaponSettingsPrototypeSID",
                "WeaponAttributesPrototypeSID", "ItemSlotType", "WeaponType",
            ):
                value = _scalar(block, field)
                if value is not None:
                    entry["fields"][field] = value
            for array_name in (
                "UpgradePrototypeSIDs", "CompatibleAttachments",
                "AttachPrototypeSIDs", "AmmoPrototypeSIDs",
            ):
                values = _array(block, array_name)
                if values:
                    entry["fields"][array_name] = values
    return result


def _upgrade_roots(game_data: Path) -> dict[str, list[str]]:
    owners: dict[str, list[str]] = defaultdict(list)
    for path in _matching_files(game_data, "UpgradePrototypes"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for sid, _, block in _top_level_blocks(text):
            target = _scalar(block, "GeneralWeaponSetupSID")
            if target:
                owners[target].append(sid)
    return {key: sorted(set(value)) for key, value in owners.items()}


def _technician_mentions(game_data: Path, setup_sids: set[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    npc_root = game_data / "NPCPrototypes"
    if not npc_root.exists():
        return {}
    for path in npc_root.rglob("*.cfg"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for sid in setup_sids:
            if sid in text:
                result[sid].append(path.relative_to(game_data).as_posix())
    return {key: sorted(set(value)) for key, value in result.items()}


def inspect_pack(name: str, root: Path) -> dict:
    roots = _game_data_roots(root)
    if not roots:
        return {"name": name, "root": str(root), "error": "No GameData directory found"}

    merged_setups: dict[str, dict] = {}
    merged_items: dict[str, dict] = {}
    upgrades: dict[str, list[str]] = defaultdict(list)
    technicians: dict[str, list[str]] = defaultdict(list)

    for game_data in roots:
        setups = _collect_family(game_data, "WeaponGeneralSetupPrototypes")
        items = _collect_family(game_data, "ItemPrototypes")
        merged_setups.update(setups)
        merged_items.update(items)
        for setup, sids in _upgrade_roots(game_data).items():
            upgrades[setup].extend(sids)
        for setup, files in _technician_mentions(game_data, set(setups)).items():
            technicians[setup].extend(files)

    weapon_setups = {}
    for sid, entry in sorted(merged_setups.items()):
        fields = entry["fields"]
        if (
            "UpgradePrototypeSIDs" in fields
            or "AmmoPrototypeSIDs" in fields
            or sid.startswith("Gun")
        ):
            weapon_setups[sid] = entry

    weapons = []
    for sid, item in sorted(merged_items.items()):
        setup = item["fields"].get("GeneralWeaponSetup")
        if not setup or setup not in weapon_setups:
            continue
        setup_entry = weapon_setups[setup]
        weapons.append({
            "weapon_sid": sid,
            "general_setup": setup,
            "weapon_refkeys": item["refkeys"],
            "setup_refkeys": setup_entry["refkeys"],
            "item_sources": item["sources"],
            "setup_sources": setup_entry["sources"],
            "pack_upgrade_roots": setup_entry["fields"].get("UpgradePrototypeSIDs", []),
            "pack_upgrade_definitions": sorted(set(upgrades.get(setup, []))),
            "compatible_attachments": setup_entry["fields"].get("CompatibleAttachments", []),
            "ammo": setup_entry["fields"].get("AmmoPrototypeSIDs", []),
            "technician_sources": sorted(set(technicians.get(setup, []))),
        })

    return {
        "name": name,
        "root": str(root),
        "game_data_roots": [str(path) for path in roots],
        "summary": {
            "weapon_items": len(weapons),
            "weapon_setups": len({weapon["general_setup"] for weapon in weapons}),
            "pack_upgrade_roots": sum(len(w["pack_upgrade_roots"]) for w in weapons),
            "pack_upgrade_definitions": sum(len(w["pack_upgrade_definitions"]) for w in weapons),
        },
        "weapons": weapons,
    }


def render(result: dict) -> str:
    lines = [
        "External weapon pack inventory",
        "==============================",
        "Local source data is read only from gitignored VanillaReference directories.",
        "",
    ]
    for pack in result["packs"]:
        lines += [pack["name"], "=" * len(pack["name"])]
        if "error" in pack:
            lines += [f"ERROR: {pack['error']}", f"Root: {pack['root']}", ""]
            continue
        s = pack["summary"]
        lines += [
            f"Weapons: {s['weapon_items']}",
            f"GeneralSetups: {s['weapon_setups']}",
            f"Referenced pack upgrade roots: {s['pack_upgrade_roots']}",
            f"Upgrade definitions targeting those setups: {s['pack_upgrade_definitions']}",
            "",
        ]
        for weapon in pack["weapons"]:
            lines.append(f"{weapon['weapon_sid']} -> {weapon['general_setup']}")
            if weapon["weapon_refkeys"]:
                lines.append(f"  item refkey: {', '.join(weapon['weapon_refkeys'])}")
            if weapon["setup_refkeys"]:
                lines.append(f"  setup refkey: {', '.join(weapon['setup_refkeys'])}")
            lines.append(f"  pack upgrade roots: {len(weapon['pack_upgrade_roots'])}")
            lines.append(f"  pack upgrade definitions: {len(weapon['pack_upgrade_definitions'])}")
            lines.append(f"  technician files: {', '.join(weapon['technician_sources']) or '-'}")
            lines.append(f"  setup source: {', '.join(weapon['setup_sources'])}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory gitignored third-party weapon packs before generating BPRUE/OXA compatibility."
    )
    parser.add_argument("--mk17-root", type=Path, default=DEFAULT_PACKS["MK17"])
    parser.add_argument("--modern-ak-root", type=Path, default=DEFAULT_PACKS["ModernAK"])
    parser.add_argument("--text-out", type=Path, default=DEFAULT_TEXT_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args()

    result = {
        "packs": [
            inspect_pack("MK17", args.mk17_root),
            inspect_pack("ModernAK", args.modern_ak_root),
        ]
    }
    text_report = render(result)
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(text_report, encoding="utf-8")
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(text_report, end="")
    print(f"Text report: {args.text_out.relative_to(ROOT).as_posix()}")
    print(f"JSON report: {args.json_out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
