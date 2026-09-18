#!/usr/bin/env python3
"""Classify Vanilla armor into helmets, suits and full-body suits."""

from __future__ import annotations
import json, re
from collections import Counter
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = Path(__file__).resolve().parent / "Reports"
ARMOR_CFG = PYTHON_ROOT / "VanillaReference" / "ArmorPrototypes.cfg"

STRUCT_START = re.compile(r"^\s*([^/\s][^:]*)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?\s*$")
FIELD_LINE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*(?:\{[^}]*\})?\s*$")
REFKEY = re.compile(r"(?:^|;)\s*refkey\s*=\s*([^;}]+)")


def parse_structs(text):
    lines=text.splitlines(); result={}; i=0
    while i < len(lines):
        m=STRUCT_START.match(lines[i])
        if not m: i+=1; continue
        name=m.group(1).strip(); attrs=m.group(2) or ""; depth=1; j=i+1
        while j < len(lines) and depth:
            depth += lines[j].count("struct.begin") - lines[j].count("struct.end"); j+=1
        ref=REFKEY.search(attrs)
        result[name]={"block":"\n".join(lines[i:j]),"refkey":ref.group(1).strip() if ref else None}
        i=j
    return result


def direct_fields(block):
    result={}; depth=0
    for line in block.splitlines()[1:-1]:
        if depth == 0 and "struct.begin" not in line:
            m=FIELD_LINE.match(line)
            if m: result[m.group(1)]=m.group(2).strip()
        depth += line.count("struct.begin") - line.count("struct.end")
    return result


def effective_fields(name, structs, stack=None):
    stack=stack or []
    if name in stack: raise ValueError("Inheritance cycle: " + " -> ".join(stack+[name]))
    entry=structs[name]; result={}; parent=entry["refkey"]
    if parent in structs: result.update(effective_fields(parent, structs, stack+[name]))
    result.update(direct_fields(entry["block"]))
    return result


FACTION_HINTS = (
    ("Dolg", "DUTY"),
    ("Duty", "DUTY"),
    ("Svoboda", "FREEDOM"),
    ("Mercenaries", "MERCENARY"),
    ("Monolith", "MONOLITH"),
    ("Spark", "SPARK"),
    ("Varta", "WARD"),
    ("Military", "MILITARY"),
    ("Neutral", "FREE_STALKER"),
    ("Bandit", "BANDIT"),
)


def faction_candidate(sid):
    """Return a conservative faction candidate derived from known SID tokens."""
    matches = [{"token": token, "faction": faction} for token, faction in FACTION_HINTS if token in sid]
    if len(matches) == 1:
        return matches[0]["faction"], matches
    if len(matches) > 1:
        return "AMBIGUOUS", matches
    return "UNRESOLVED", []


def classify(slot, block_head):
    if slot == "EInventoryEquipmentSlot::Head": return "HELMET"
    if slot == "EInventoryEquipmentSlot::Body" and block_head == "false": return "SUIT"
    if slot == "EInventoryEquipmentSlot::Body" and block_head == "true": return "FULL_BODY_SUIT"
    if slot == "EInventoryEquipmentSlot::Body": return "AMBIGUOUS_BODY"
    return "UNCLASSIFIED"


def main():
    structs=parse_structs(ARMOR_CFG.read_text(encoding="utf-8"))
    templates={"TemplateArmor","TemplateHelmet"}; rows=[]
    excluded=[]
    for name,entry in structs.items():
        direct=direct_fields(entry["block"]); fields=effective_fields(name,structs)
        sid=fields.get("SID",name)
        faction,matches=faction_candidate(sid)
        if name.startswith("NPC_") or sid.startswith("NPC_"):
            excluded.append({"sid":sid,"struct":name,"reason":"NPC_PREFIX","refkey":entry["refkey"]})
            continue
        rows.append({
            "sid":sid,"struct":name,
            "category":classify(fields.get("ItemSlotType"),fields.get("bBlockHead")),
            "item_slot_type":fields.get("ItemSlotType"),
            "blocks_head": {"true":True,"false":False}.get(fields.get("bBlockHead")),
            "refkey":entry["refkey"],
            "direct_item_slot_type":direct.get("ItemSlotType"),
            "direct_bBlockHead":direct.get("bBlockHead"),
            "faction_candidate":faction,
            "faction_matches":matches,
        })
    concrete=[r for r in rows if r["struct"] not in templates]
    faction_groups={}
    for faction in [x[1] for x in FACTION_HINTS]+["AMBIGUOUS","UNRESOLVED"]:
        faction_groups[faction]=sorted(
            [r for r in concrete if r["faction_candidate"]==faction],
            key=lambda r:(r["category"],r["sid"])
        )
    categories={k:sorted([r for r in concrete if r["category"]==k],key=lambda r:r["sid"])
                for k in ("HELMET","SUIT","FULL_BODY_SUIT","AMBIGUOUS_BODY","UNCLASSIFIED")}
    payload={
        "classification_rules":{
            "HELMET":"effective ItemSlotType == EInventoryEquipmentSlot::Head",
            "SUIT":"effective ItemSlotType == EInventoryEquipmentSlot::Body and bBlockHead == false",
            "FULL_BODY_SUIT":"effective ItemSlotType == EInventoryEquipmentSlot::Body and bBlockHead == true"},
        "templates":[r for r in rows if r["struct"] in templates],
        "excluded":excluded,
        "faction_hint_rules":{token:faction for token,faction in FACTION_HINTS},
        "faction_counts":{k:len(v) for k,v in faction_groups.items()},
        "factions":faction_groups,
        "counts":{k:len(v) for k,v in categories.items()},
        "categories":categories}
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    out=REPORT_DIR/"armor_classification.json"
    out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    counts=Counter(r["category"] for r in concrete)
    print("=== BPRUE Vanilla Armor Classification ===")
    print(f"Concrete player armor prototypes: {len(concrete)}")
    print(f"Excluded NPC_* prototypes: {len(excluded)}")
    for k in categories: print(f"{k}: {counts[k]}")
    print("\n=== Faction / Class Candidates ===")
    for faction,items in faction_groups.items():
        print(f"{faction}: {len(items)}")
    if faction_groups["UNRESOLVED"] or faction_groups["AMBIGUOUS"]:
        print("\n=== Faction candidates needing manual resolution ===")
        for r in faction_groups["AMBIGUOUS"]+faction_groups["UNRESOLVED"]:
            matches=", ".join(f"{m['token']}->{m['faction']}" for m in r["faction_matches"]) or "no safe SID hint"
            print(f"{r['sid']} [{r['category']}]: {matches}")
    print("\n=== Full Body Suits ===")
    for r in categories["FULL_BODY_SUIT"]: print(r["sid"])
    if categories["AMBIGUOUS_BODY"] or categories["UNCLASSIFIED"]:
        print("\n=== Needs inspection ===")
        for r in categories["AMBIGUOUS_BODY"]+categories["UNCLASSIFIED"]:
            print(f"{r['sid']}: slot={r['item_slot_type']} bBlockHead={r['blocks_head']}")
    print(f"\nReport written to: {out}")
    return 1 if categories["AMBIGUOUS_BODY"] or categories["UNCLASSIFIED"] else 0

if __name__=="__main__":
    raise SystemExit(main())
