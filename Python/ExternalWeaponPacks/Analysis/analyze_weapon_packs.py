from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_VANILLA_ROOT = ROOT / "Python/VanillaReference"
REGISTRY_PATH = ROOT / "Python/ExternalWeaponPacks/weapon_packs.json"
DEFAULT_TEXT_OUT = ROOT / "Python/ExternalWeaponPacks/Reports/weapon_packs.txt"
DEFAULT_JSON_OUT = ROOT / "Python/ExternalWeaponPacks/Reports/weapon_packs.json"

TOP_LEVEL = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?")
SCALAR = re.compile(r"(?m)^\s*{name}\s*=\s*([^\s/]+)")
ARRAY = re.compile(r"(?ms)^\s*{name}\s*:\s*struct\.begin(?:\s*\{{[^}}]*\}})?\s*(.*?)^\s*struct\.end")
INDEXED = re.compile(r"(?m)^\s*\[(\d+)\]\s*=\s*([^\s/]+)")
UPGRADE_SID = re.compile(r"(?m)^\s*UpgradePrototypeSID\s*=\s*([^\s/]+)")


def load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def game_data_roots(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.name == "GameData":
        return [root]
    return sorted(path for path in root.rglob("GameData") if path.is_dir())


def matching_files(game_data: Path, fragment: str) -> list[Path]:
    return sorted(path for path in game_data.rglob("*.cfg") if fragment.lower() in path.as_posix().lower())


def top_level_blocks(text: str):
    text = text.lstrip("\ufeff")
    matches = list(TOP_LEVEL.finditer(text))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield match.group(1), match.group(2) or "", text[match.start():end]


def scalar(block: str, name: str) -> str | None:
    match = re.search(SCALAR.pattern.format(name=re.escape(name)), block)
    return match.group(1) if match else None


def array(block: str, name: str) -> list[str]:
    match = re.search(ARRAY.pattern.format(name=re.escape(name)), block)
    if not match:
        return []
    indexed = [(int(index), value) for index, value in INDEXED.findall(match.group(1))]
    return [value for _, value in sorted(indexed)]


def refkey(modes: str) -> str | None:
    match = re.search(r"(?:^|;)\s*refkey\s*=\s*([^;}]+)", modes)
    return match.group(1).strip() if match else None


def collect_family(game_data: Path, fragment: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for path in matching_files(game_data, fragment):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for sid, modes, block in top_level_blocks(text):
            entry = result.setdefault(sid, {"sid": sid, "sources": [], "refkeys": [], "fields": {}})
            entry["sources"].append(path.relative_to(game_data).as_posix())
            parent = refkey(modes)
            if parent and parent not in entry["refkeys"]:
                entry["refkeys"].append(parent)
            for field in ("SID", "GeneralWeaponSetup", "PlayerWeaponAttributes", "NPCWeaponAttributes", "ItemSlotType", "WeaponType", "AmmoCaliber"):
                value = scalar(block, field)
                if value is not None:
                    entry["fields"][field] = value.removeprefix("EAmmoCaliber::")
            for array_name in ("UpgradePrototypeSIDs", "CompatibleAttachments", "AttachPrototypeSIDs"):
                values = array(block, array_name)
                if values:
                    entry["fields"][array_name] = values
    return result


def effective_entry(entries: dict[str, dict], sid: str) -> tuple[dict, list[str]]:
    """Resolve scalar/array fields through refkey inheritance, child values winning."""
    fields: dict = {}
    chain: list[str] = []
    visiting: set[str] = set()

    def visit(current_sid: str) -> None:
        if current_sid in visiting:
            raise ValueError(f"Circular refkey inheritance: {' -> '.join(chain + [current_sid])}")
        entry = entries.get(current_sid)
        if entry is None:
            return
        visiting.add(current_sid)
        parents = entry.get("refkeys", [])
        if parents:
            visit(parents[-1])
        fields.update(entry.get("fields", {}))
        chain.append(current_sid)
        visiting.remove(current_sid)

    visit(sid)
    return fields, chain


def collect_upgrade_definitions(game_data: Path) -> set[str]:
    result = set()
    upgrade_root = game_data / "UpgradePrototypes"
    if not upgrade_root.exists():
        return result
    for path in upgrade_root.rglob("*.cfg"):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        result.update(sid for sid, _, _ in top_level_blocks(text))
    return result


def technician_owners(game_data: Path, upgrade_roots: set[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    npc_root = game_data / "NPCPrototypes"
    if not npc_root.exists() or not upgrade_roots:
        return {}
    for path in npc_root.rglob("*.cfg"):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        for technician_sid, _, block in top_level_blocks(text):
            owned = sorted(set(UPGRADE_SID.findall(block)) & upgrade_roots)
            if owned:
                result[technician_sid].extend(owned)
    return {sid: sorted(set(values)) for sid, values in result.items()}


def inspect_pack(pack_name: str, spec: dict, vanilla_root: Path) -> dict:
    root = vanilla_root / spec["reference_root"]
    roots = game_data_roots(root)
    if not roots:
        return {"name": pack_name, "root": str(root), "error": "No GameData directory found"}
    setups, items, upgrade_defs = {}, {}, set()
    for game_data in roots:
        setups.update(collect_family(game_data, "WeaponGeneralSetupPrototypes"))
        items.update(collect_family(game_data, "ItemPrototypes"))
        upgrade_defs.update(collect_upgrade_definitions(game_data))

    weapons, all_pack_roots = [], set()
    for weapon_spec in spec["weapons"]:
        weapon_sid, setup_sid = weapon_spec["weapon_sid"], weapon_spec["general_setup_sid"]
        item, setup = items.get(weapon_sid), setups.get(setup_sid)
        errors = []
        if item is None: errors.append("weapon prototype not found")
        if setup is None: errors.append("GeneralSetup not found")
        effective_fields, inheritance_chain = effective_entry(setups, setup_sid) if setup else ({}, [])
        roots_for_weapon = effective_fields.get("UpgradePrototypeSIDs", [])
        all_pack_roots.update(roots_for_weapon)
        weapons.append({
            **weapon_spec, "category": spec["category"],
            "detected_caliber": effective_fields.get("AmmoCaliber"),
            "setup_inheritance_chain": inheritance_chain,
            "weapon_refkeys": item["refkeys"] if item else [],
            "setup_refkeys": setup["refkeys"] if setup else [],
            "item_sources": item["sources"] if item else [],
            "setup_sources": setup["sources"] if setup else [],
            "pack_upgrade_roots": roots_for_weapon,
            "pack_upgrade_definitions": sorted(set(roots_for_weapon) & upgrade_defs),
            "errors": errors,
        })

    techs = {}
    for game_data in roots:
        for technician_sid, owned in technician_owners(game_data, all_pack_roots).items():
            techs.setdefault(technician_sid, []).extend(owned)
    techs = {sid: sorted(set(values)) for sid, values in techs.items()}
    return {
        "name": pack_name, "root": str(root), "category": spec["category"],
        "game_data_roots": [str(path) for path in roots],
        "summary": {
            "weapon_items": len(weapons),
            "weapon_setups": len({weapon["general_setup_sid"] for weapon in weapons}),
            "pack_upgrade_roots": len(all_pack_roots),
            "resolved_upgrade_definitions": len(all_pack_roots & upgrade_defs),
            "technicians": len(techs),
        },
        "technicians": techs, "weapons": weapons,
    }


def render(result: dict) -> str:
    lines = ["External weapon pack inventory", "==============================", "Local source data is read only from gitignored VanillaReference directories.", "Weapon category is explicit registry data; it is not guessed from CFG inheritance.", ""]
    for pack in result["packs"]:
        lines += [pack["name"], "=" * len(pack["name"])]
        if "error" in pack:
            lines += [f"ERROR: {pack['error']}", f"Root: {pack['root']}", ""]
            continue
        s = pack["summary"]
        lines += [f"Category: {pack['category']}", f"Weapons: {s['weapon_items']}", f"GeneralSetups: {s['weapon_setups']}", f"Unique pack upgrade roots: {s['pack_upgrade_roots']}", f"Resolved upgrade definitions: {s['resolved_upgrade_definitions']}", f"Technicians supporting pack upgrades: {s['technicians']}", ""]
        for weapon in pack["weapons"]:
            lines.append(f"{weapon['weapon_sid']} -> {weapon['general_setup_sid']} [{weapon['base_caliber']}]")
            if weapon["detected_caliber"]: lines.append(f"  detected caliber: {weapon['detected_caliber']}")
            if len(weapon.get("setup_inheritance_chain", [])) > 1:
                lines.append(f"  setup inheritance: {' -> '.join(weapon['setup_inheritance_chain'])}")
            lines.append(f"  pack upgrade roots: {len(weapon['pack_upgrade_roots'])}")
            lines.append(f"  resolved definitions: {len(weapon['pack_upgrade_definitions'])}")
            if weapon["errors"]: lines.append(f"  ERRORS: {', '.join(weapon['errors'])}")
            lines.append(f"  setup source: {', '.join(weapon['setup_sources']) or '-'}")
        if pack["technicians"]:
            lines.append("  technicians:")
            for technician_sid, owned in sorted(pack["technicians"].items()):
                lines.append(f"    {technician_sid}: {len(owned)} matching pack upgrades")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory registered third-party weapon packs for BPRUE compatibility.")
    parser.add_argument("--vanilla-root", type=Path, default=DEFAULT_VANILLA_ROOT)
    parser.add_argument("--text-out", type=Path, default=DEFAULT_TEXT_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args()
    registry = load_registry()
    result = {"packs": [inspect_pack(name, spec, args.vanilla_root) for name, spec in registry["packs"].items()]}
    text_report = render(result)
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(text_report, encoding="utf-8")
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(text_report, end="")
    print(f"Text report: {args.text_out.relative_to(ROOT).as_posix()}")
    print(f"JSON report: {args.json_out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
