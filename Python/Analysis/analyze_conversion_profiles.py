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
                    # Generator tables contain icon helper calls. Ignore their display-only
                    # values without importing generators or executing code.
                    class IgnoreIcons(ast.NodeTransformer):
                        def visit_Call(self, call):
                            if isinstance(call.func, ast.Name) and call.func.id == "_ammo_icon":
                                return ast.copy_location(ast.Constant(value=None), call)
                            raise ValueError(f"Unexpected call in {name}: {ast.unparse(call)}")
                    return ast.literal_eval(IgnoreIcons().visit(node.value))
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
        value = value.replace(old, new) if old != "Effect" else re.sub(r"Effect$", "", value)
    value = re.sub(r"(?<=\D)(\d+)$", r" \1%", value)
    return re.sub(r"\s+", " ", value).strip()

def add(rows, weapon_class, weapon, source, target, effects, variant="Default"):
    rows.append({
        "class": weapon_class,
        "weapon": weapon,
        "source": source,
        "target": target,
        "effects": tuple(effects),
        "variant": variant,
    })

def collect_ar(rows):
    cfg = load_json(CONFIGS["AR"])
    gen = GENERATORS["AR"]
    power = literal_assignment(gen, "POWER_CALIBER")
    effects = literal_assignment(gen, "CALIBER_EFFECTS")
    variant_tables = {
        "A762": literal_assignment(gen, "A762_CONVERSION_VARIANTS"),
        "A762Sniper": literal_assignment(gen, "A762SNIPER_CONVERSION_VARIANTS"),
        "A762NATO": literal_assignment(gen, "A762NATO_CONVERSION_VARIANTS"),
    }
    for name, family in cfg["families"].items():
        source = family["base_caliber"]
        targets = []
        if family.get("bprue_caliber_conversion", True) and source in power:
            targets.append(power[source][0])
        targets.extend(family.get("additional_caliber_conversions", []))
        for target in targets:
            variants = variant_tables.get(target)
            if variants:
                for variant, spec in variants.items():
                    add(rows, "AR", name, source, target, spec["stat_effects"], variant)
            else:
                add(rows, "AR", name, source, target, effects[target][3])

def collect_smg(rows):
    cfg = load_json(CONFIGS["SMG"])
    gen = GENERATORS["SMG"]
    stat_effects = literal_assignment(gen, "CALIBER_STAT_EFFECTS")
    for name, family in cfg["caliber_families"].items():
        if not family.get("bprue_caliber_conversion", True):
            continue
        source = family["base_caliber"]
        prefix = family["prototype_prefix"]
        for target in family["conversions"]:
            table_name = None
            if prefix == "GunM10" and target in ("A919", "A918"):
                table_name = f"M10_{target}_VARIANTS"
            elif prefix == "GunBucket" and target in ("A919", "A045"):
                table_name = f"BUCKET_{target}_VARIANTS"
            elif prefix == "GunZubr" and target in ("A918", "A045"):
                table_name = f"ZUBR_{target}_VARIANTS"
            if table_name:
                for variant, spec in literal_assignment(gen, table_name).items():
                    add(rows, "SMG", name, source, target, spec["stat_effects"], variant)
            else:
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
            target = conversion["target"]
            for variant, spec in conversion["variants"].items():
                add(rows, "Sniper", name, source, target, spec[4], variant)

def print_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row["class"], row["source"], row["target"], row["variant"], row["effects"])
        grouped[key].append(row["weapon"])

    print("BPRUE caliber conversion stat profiles")
    print()
    for (weapon_class, source, target, variant, effects), weapons in sorted(grouped.items()):
        print(f"{weapon_class}: {', '.join(sorted(weapons))}")
        print(f"  Conversion: {source} -> {target} ({variant})")
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
