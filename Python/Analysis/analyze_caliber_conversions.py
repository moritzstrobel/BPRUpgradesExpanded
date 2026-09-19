from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

PYTHON_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PYTHON_ROOT.parent
VANILLA_ROOT = PYTHON_ROOT / "VanillaReference"
REPORT_PATH = PYTHON_ROOT / "Analysis" / "Reports" / "caliber_conversion_matrix.json"

STRUCT_START_RE = re.compile(r"^\s*([^\s:]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?")
STRUCT_END_RE = re.compile(r"^\s*struct\.end\s*$")
ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][\w]*)\s*=\s*(.*?)\s*(?://.*)?$")
ARRAY_ITEM_RE = re.compile(r"^\s*\[(?:\*|\d+)\]\s*=\s*([^\s{]+)")
CALIBER_RE = re.compile(r"EAmmoCaliber::([A-Za-z0-9_]+)")


def cfg_files(root: Path):
    if not root.exists():
        return
    yield from root.rglob("*.cfg")


def parse_blocks(path: Path):
    stack = []
    current = None
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return
    for line_no, line in enumerate(lines, 1):
        start = STRUCT_START_RE.match(line)
        if start:
            name, attrs = start.groups()
            block = {"name": name, "attrs": attrs or "", "fields": {}, "arrays": defaultdict(list),
                     "path": str(path.relative_to(REPO_ROOT)), "line": line_no}
            stack.append((name, block))
            if len(stack) == 1:
                current = block
            continue
        if STRUCT_END_RE.match(line):
            if stack:
                stack.pop()
            if not stack:
                if current:
                    yield current
                current = None
            continue
        if not stack or current is None:
            continue
        field = ASSIGN_RE.match(line)
        if field and len(stack) == 1:
            current["fields"][field.group(1)] = field.group(2).strip()
            continue
        item = ARRAY_ITEM_RE.match(line)
        if item and len(stack) >= 2:
            current["arrays"][stack[-1][0]].append(item.group(1).strip())


def clean(value: str | None):
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


def load_vanilla():
    effects = {}
    upgrades = {}
    setups = {}
    for path in cfg_files(VANILLA_ROOT):
        for block in parse_blocks(path):
            sid = clean(block["fields"].get("SID")) or block["name"]
            if not sid or sid.startswith("["):
                continue
            fields = block["fields"]
            if "Caliber" in fields and ("Effect" in sid or "ChangeCaliber" in sid):
                m = CALIBER_RE.search(fields["Caliber"])
                if m:
                    effects[sid] = {"caliber": m.group(1), "source": block["path"], "line": block["line"]}
            effect_sids = block["arrays"].get("EffectPrototypeSIDs", [])
            if effect_sids:
                upgrades[sid] = {"effects": effect_sids, "source": block["path"], "line": block["line"]}
            upgrade_sids = block["arrays"].get("Upgrades", [])
            if upgrade_sids:
                setups[sid] = {"upgrades": upgrade_sids, "source": block["path"], "line": block["line"]}
    return effects, upgrades, setups


def vanilla_conversions(effects, upgrades, setups):
    conversion_upgrades = {}
    for sid, data in upgrades.items():
        targets = sorted({effects[e]["caliber"] for e in data["effects"] if e in effects})
        if targets:
            conversion_upgrades[sid] = {**data, "targets": targets}

    by_setup = defaultdict(list)
    for setup_sid, data in setups.items():
        for upgrade_sid in data["upgrades"]:
            if upgrade_sid in conversion_upgrades:
                by_setup[setup_sid].append({"upgrade_sid": upgrade_sid, **conversion_upgrades[upgrade_sid]})
    return conversion_upgrades, by_setup


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def bprue_rows():
    rows = []

    ar = load_json(PYTHON_ROOT / "CFGGenerators" / "AssaultRifles" / "assault_rifles_upgrades.json")
    for name, family in ar["families"].items():
        targets = []
        if family.get("bprue_caliber_conversion", True):
            targets += {"A545": ["A762Sniper"], "A556": ["A762NATO"]}.get(family["base_caliber"], [])
        targets += family.get("additional_caliber_conversions", [])
        rows.append(("AR", name, family["weapon_sid"], family["general_setup_sid"], family["base_caliber"], targets,
                     not family.get("bprue_caliber_conversion", True)))

    smg = load_json(PYTHON_ROOT / "CFGGenerators" / "SMGs" / "smg_upgrades.json")
    smg_weapons = {k: v["weapon_sid"] for k, v in smg["families"].items()}
    for name, family in smg.get("caliber_families", {}).items():
        enabled = family.get("bprue_caliber_conversion", True)
        rows.append(("SMG", name, smg_weapons.get(name), family["general_setup_sid"], family["base_caliber"],
                     family["conversions"] if enabled else [], not enabled))

    sn = load_json(PYTHON_ROOT / "CFGGenerators" / "Snipers" / "sniper_upgrades.json")
    sniper_targets = {"A762Sniper": ["A762NATO"], "A762NATO": ["A762Sniper"]}
    for name, family in sn["families"].items():
        enabled = family.get("bprue_caliber_conversion", True)
        rows.append(("Sniper", name, family["weapon_sid"], family["general_setup_sid"], family["base_caliber"],
                     sniper_targets.get(family["base_caliber"], []) if enabled else [], not enabled))
    return rows


def main():
    parser = argparse.ArgumentParser(description="Audit Vanilla and BPRUE caliber conversions.")
    parser.add_argument("--json", type=Path, default=REPORT_PATH, help="JSON report output path")
    parser.add_argument("--no-json", action="store_true", help="Do not write the JSON report")
    args = parser.parse_args()

    effects, upgrades, setups = load_vanilla()
    conversion_upgrades, by_setup = vanilla_conversions(effects, upgrades, setups)

    report_rows = []
    for weapon_class, name, weapon_sid, setup_sid, base, bprue, disabled in bprue_rows():
        vanilla = by_setup.get(setup_sid, [])
        vanilla_targets = sorted({target for item in vanilla for target in item["targets"]})
        report_rows.append({
            "class": weapon_class,
            "weapon": name,
            "weapon_sid": weapon_sid,
            "general_setup_sid": setup_sid,
            "base_caliber": base,
            "vanilla_conversions": vanilla_targets,
            "vanilla_upgrade_sids": [item["upgrade_sid"] for item in vanilla],
            "bprue_conversions": bprue,
            "bprue_conversion_disabled": disabled,
        })

    headers = ("Class", "Weapon", "Base", "Vanilla", "BPRUE", "Disabled")
    printable = []
    for row in report_rows:
        printable.append((
            row["class"], row["weapon"], row["base"],
            ", ".join(row["vanilla_conversions"]) or "-",
            ", ".join(row["bprue_conversions"]) or "-",
            "yes" if row["bprue_conversion_disabled"] else "-",
        ))
    widths = [max(len(headers[i]), *(len(r[i]) for r in printable)) for i in range(len(headers))]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * w for w in widths))
    for row in printable:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))

    if not args.no_json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": {
                "vanilla_change_caliber_effects": len(effects),
                "vanilla_conversion_upgrades": len(conversion_upgrades),
                "tracked_weapon_families": len(report_rows),
            },
            "weapons": report_rows,
            "vanilla_conversion_upgrades": conversion_upgrades,
        }
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
