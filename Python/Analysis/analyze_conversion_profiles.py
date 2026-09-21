from __future__ import annotations

import ast
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = {
    "AR": ROOT / "Python/CFGGenerators/AssaultRifles/generate_assault_rifle_upgrades.py",
    "SMG": ROOT / "Python/CFGGenerators/SMGs/generate_smg_upgrades.py",
    "Sniper": ROOT / "Python/CFGGenerators/Snipers/generate_sniper_upgrades.py",
}
CONFIGS = {
    "AR": ROOT / "Python/CFGGenerators/AssaultRifles/assault_rifles_upgrades.json",
    "SMG": ROOT / "Python/CFGGenerators/SMGs/smg_upgrades.json",
    "Sniper": ROOT / "Python/CFGGenerators/Snipers/sniper_upgrades.json",
}

def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path}")

def load_json(path: Path):
    import json
    return json.loads(path.read_text(encoding="utf-8"))

def effect_label(sid: str) -> str:
    replacements = (
        ("BPRUE_Shared_", ""), ("BPRUE_SMG_", ""), ("BPRUE_Sniper_", ""), ("BPRUE_", ""),
        ("Effect", ""), ("Pos", " +"), ("Penalty", " penalty "), ("Neg", " -"),
    )
    value = sid
    for old, new in replacements:
        value = value.replace(old, new)
    value = re.sub(r"(?<=\D)(\d+)$", r" \1%", value)
    return re.sub(r"\s+", " ", value).strip()

def add(rows, weapon_class, weapon, source, target, effects):
    rows.append({
        "class": weapon_class,
        "weapon": weapon,
        "source": source,
        "target": target,
        "effects": tuple(effects),
    })

def collect_ar(rows):
    cfg = load_json(CONFIGS["AR"])
    gen = GENERATORS["AR"]
    power = literal_assignment(gen, "POWER_CALIBER")
    effects = literal_assignment(gen, "CALIBER_EFFECTS")
    for name, family in cfg["families"].items():
        source = family["base_caliber"]
        if family.get("bprue_caliber_conversion", True) and source in power:
            target = power[source][0]
            add(rows, "AR", name, source, target, effects[target][3])
        for target in family.get("additional_caliber_conversions", []):
            add(rows, "AR", name, source, target, effects[target][3])

def collect_smg(rows):
    cfg = load_json(CONFIGS["SMG"])
    stat_effects = literal_assignment(GENERATORS["SMG"], "CALIBER_STAT_EFFECTS")
    for name, family in cfg["caliber_families"].items():
        if not family.get("bprue_caliber_conversion", True):
            continue
        source = family["base_caliber"]
        for target in family["conversions"]:
            add(rows, "SMG", name, source, target, stat_effects.get((source, target), ()))

def collect_sniper(rows):
    cfg = load_json(CONFIGS["Sniper"])
    conversions = literal_assignment(GENERATORS["Sniper"], "CALIBER_CONVERSIONS")
    for name, family in cfg["families"].items():
        if not family.get("bprue_caliber_conversion", True):
            continue
        source = family["base_caliber"]
        conversion = conversions.get(source)
        if conversion:
            target = conversion[0]
            add(rows, "Sniper", name, source, target, conversion[5][3:])

def print_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row["class"], row["source"], row["target"], row["effects"])
        grouped[key].append(row["weapon"])

    print("BPRUE caliber conversion stat profiles")
    print()
    for (weapon_class, source, target, effects), weapons in sorted(grouped.items()):
        print(f"{weapon_class}: {', '.join(sorted(weapons))}")
        print(f"  Conversion: {source} -> {target}")
        if effects:
            print("  Stat effects:")
            for sid in effects:
                print(f"    {sid}")
                print(f"      {effect_label(sid)}")
        else:
            print("  Stat effects: none")
        print()

def main():
    rows = []
    collect_ar(rows)
    collect_smg(rows)
    collect_sniper(rows)
    print_rows(rows)

if __name__ == "__main__":
    main()
