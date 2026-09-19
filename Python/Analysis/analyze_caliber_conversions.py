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
            # WeaponGeneralSetupPrototypes uses UpgradePrototypeSIDs. Keep the
            # older/generic "Upgrades" alias as a fallback for other scopes.
            upgrade_sids = (
                block["arrays"].get("UpgradePrototypeSIDs", [])
                or block["arrays"].get("Upgrades", [])
            )
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


def load_ammo_catalog():
    """Collect Vanilla ammo variants by caliber, including inherited caliber."""
    blocks = {}
    for path in cfg_files(VANILLA_ROOT):
        if path.name != "AmmoPrototypes.cfg":
            continue
        for block in parse_blocks(path):
            sid = clean(block["fields"].get("SID")) or block["name"]
            if sid and not sid.startswith("["):
                ref = re.search(r"refkey=([^;}]*)", block["attrs"])
                blocks[sid] = {
                    "sid": sid,
                    "refkey": clean(ref.group(1)) if ref else None,
                    "fields": block["fields"],
                    "source": block["path"],
                    "line": block["line"],
                }

    def inherited_field(sid, field, seen=None):
        seen = set() if seen is None else seen
        if sid in seen or sid not in blocks:
            return None
        seen.add(sid)
        block = blocks[sid]
        value = block["fields"].get(field)
        if value is not None:
            return value
        ref = block["refkey"]
        if ref and ref != "[0]":
            return inherited_field(ref, field, seen)
        return None

    catalog = defaultdict(list)
    for sid, block in blocks.items():
        caliber_value = inherited_field(sid, "Caliber")
        match = CALIBER_RE.search(caliber_value or "")
        if not match or match.group(1) == "None":
            continue
        catalog[match.group(1)].append({
            "sid": sid,
            "ammo_type": clean(inherited_field(sid, "AmmoType")),
            "projectile_sid": clean(inherited_field(sid, "ProjectilePrototypeSID")),
            "source": block["source"],
            "line": block["line"],
        })
    return dict(catalog)


AMMO_VARIANT_ORDER = ("Default", "ArmorPiercing", "Expanding", "Supersonic")


def ammo_variant_matrix(ammo_catalog):
    """Summarize the actually defined Vanilla ammo types for every caliber."""
    matrix = {}
    for caliber, ammo in sorted(ammo_catalog.items()):
        variants = defaultdict(list)
        for item in ammo:
            if item["sid"] == "TemplateAmmo":
                continue
            ammo_type = item["ammo_type"] or "Unknown"
            variants[ammo_type].append(item["sid"])
        ordered = {kind: sorted(variants.pop(kind, [])) for kind in AMMO_VARIANT_ORDER}
        ordered.update({kind: sorted(sids) for kind, sids in sorted(variants.items())})
        matrix[caliber] = ordered
    return matrix


def print_ammo_variant_matrix(matrix):
    print()
    print("Vanilla ammo variant matrix:")
    headers = ("Caliber", *AMMO_VARIANT_ORDER, "Variants")
    rows = []
    for caliber, variants in matrix.items():
        rows.append((caliber, *(" / ".join(variants.get(kind, [])) or "-" for kind in AMMO_VARIANT_ORDER), str(sum(bool(variants.get(kind)) for kind in AMMO_VARIANT_ORDER))))
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def caliber_support(effects, ammo_catalog):
    by_caliber = defaultdict(lambda: {"change_caliber_effects": [], "ammo": []})
    for sid, data in effects.items():
        by_caliber[data["caliber"]]["change_caliber_effects"].append(sid)
    for caliber, ammo in ammo_catalog.items():
        by_caliber[caliber]["ammo"] = ammo
    return dict(by_caliber)


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
    ammo_catalog = load_ammo_catalog()
    support = caliber_support(effects, ammo_catalog)
    ammo_matrix = ammo_variant_matrix(ammo_catalog)

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

    # Highlight weapons that are safe candidates for new BPRUE conversions:
    # no Vanilla caliber conversion and no BPRUE caliber conversion yet.
    for row in report_rows:
        row["candidate"] = (
            not row["vanilla_conversions"]
            and not row["bprue_conversions"]
            and not row["bprue_conversion_disabled"]
        )

    print_ammo_variant_matrix(ammo_matrix)
    headers = ("Class", "Weapon", "Base", "Vanilla", "BPRUE", "Candidate")
    printable = []
    for row in report_rows:
        printable.append((
            row["class"], row["weapon"], row["base_caliber"],
            ", ".join(row["vanilla_conversions"]) or "-",
            ", ".join(row["bprue_conversions"]) or "-",
            "YES" if row["candidate"] else "-",
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
                "vanilla_general_setups_with_upgrades": len(setups),
                "conversion_candidates": sum(1 for row in report_rows if row["candidate"]),
            },
            "weapons": report_rows,
            "vanilla_conversion_upgrades": conversion_upgrades,
            "caliber_support": support,
            "ammo_variant_matrix": ammo_matrix,
            }
        args.json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"\nWrote {args.json.relative_to(REPO_ROOT)}")

    candidates = [row for row in report_rows if row["candidate"]]
    if candidates:
        print("\nConversion candidates (no Vanilla/BPRUE caliber conversion):")
        for row in candidates:
            print(f"  {row['class']:<6} {row['weapon']:<12} {row['base_caliber']}")

        candidate_bases = sorted({row["base_caliber"] for row in candidates})
        print("\nAvailable Vanilla target-caliber building blocks:")
        for caliber in sorted(support):
            if caliber in candidate_bases:
                continue
            data = support[caliber]
            effects_text = ", ".join(sorted(data["change_caliber_effects"])) or "-"
            ammo_text = ", ".join(
                f"{a['sid']}[{a['ammo_type'] or '?'}]"
                for a in data["ammo"]
                if a["sid"] != "TemplateAmmo"
            ) or "-"
            print(f"  {caliber}")
            print(f"    ChangeCaliber effects: {effects_text}")
            print(f"    Ammo: {ammo_text}")


if __name__ == "__main__":
    main()
