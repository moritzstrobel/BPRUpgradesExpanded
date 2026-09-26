#!/usr/bin/env python3
"""Compare BPRUE generic Armor module values against observed Vanilla armor mechanics.

Read-only analysis helper. It does not rewrite armor_modules.json.
"""
from __future__ import annotations
import json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "Python/AnalysisArmor/Reports/armor_mechanic_inventory.json"
MODULES = ROOT / "Python/CFGGenerators/Armor/armor_modules.json"
OUT = ROOT / "Python/AnalysisArmor/Reports/armor_module_balance.json"

CATEGORIES = ("HELMET", "SUIT", "FULL_BODY_SUIT")
TRACKED = {
    "ProtectionStrike", "ProtectionBurn", "ProtectionChemical", "ProtectionShock",
    "ProtectionRadiation", "MaxDurability", "ArmorItemWeight", "RegenStamina",
    "AdditionalInventoryWeight", "PenaltyLessWeight",
}

def number(value):
    if isinstance(value, (int, float)): return float(value)
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)%?\s*", str(value))
    return float(m.group(1)) if m else None

def observed_values(counts):
    values=[]
    for raw,count in (counts or {}).items():
        n=number(raw)
        if n is not None: values.extend([n]*int(count))
    return sorted(values)

def percentile(values, q):
    if not values: return None
    pos=(len(values)-1)*q; lo=int(pos); hi=min(lo+1,len(values)-1); frac=pos-lo
    return values[lo]*(1-frac)+values[hi]*frac

def main():
    inventory=json.loads(INVENTORY.read_text(encoding="utf-8"))
    modules=json.loads(MODULES.read_text(encoding="utf-8"))["modules"]
    vanilla={}
    for row in inventory:
        typ=row["type"].split("::")[-1]
        if typ not in TRACKED: continue
        vals=observed_values(row.get("value_min_counts"))
        vanilla[typ]={
            "upgrade_count":row["upgrade_count"], "armor_count":row["armor_count"],
            "distribution":row.get("value_min_counts", {}),
            "min":min(vals) if vals else None, "median":percentile(vals,.5),
            "p75":percentile(vals,.75), "max":max(vals) if vals else None,
        }

    rows=[]
    for module_id,module in modules.items():
        for category in CATEGORIES:
            for effect in module["effects"].get(category, []):
                typ=effect["type"]; value=number(effect["value"])
                rows.append({
                    "module":module_id, "group":module["group"], "category":category,
                    "effect":typ, "value":effect["value"], "numeric_value":value,
                    "positive":effect.get("positive"),
                    "vanilla":vanilla.get(typ),
                })

    result={"vanilla":vanilla,"module_effects":rows}
    OUT.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")

    print("Vanilla armor mechanic ranges")
    for typ,data in vanilla.items():
        print(f"{typ:28} min={data['min']:>5g} median={data['median']:>5g} p75={data['p75']:>5g} max={data['max']:>5g}")
    print("\nCurrent generic modules")
    for module_id,module in modules.items():
        print(f"\n{module_id} [{module['group']}]")
        for category in CATEGORIES:
            effects=", ".join(f"{e['type']}={e['value']}" for e in module["effects"].get(category, []))
            print(f"  {category:14} {effects}")
    print(f"\nWrote {OUT.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
