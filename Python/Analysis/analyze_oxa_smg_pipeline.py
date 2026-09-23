from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from analyze_oxa_conflicts import (
    ROOT,
    Write,
    _apply_array_patch,
    _entry_identity,
    _semantic_array_root,
    _semantic_arrays,
    _writes_by_semantic_group,
    collect,
    collect_vanilla,
)

DEFAULT_OXA_ROOT = ROOT / "Python/VanillaReference/OxaData"
DEFAULT_BPRUE_ROOT = ROOT / "GameLite"
DEFAULT_COMPAT_ROOT = ROOT / "Compat/OXA/GameLite"
DEFAULT_REPORT = ROOT / "Python/Analysis/Reports/oxa_conflicts.json"
DEFAULT_TEXT_OUT = ROOT / "Python/Analysis/Reports/oxa_smg_pipeline.txt"
DEFAULT_JSON_OUT = ROOT / "Python/Analysis/Reports/oxa_smg_pipeline.json"

WATCH_ARRAYS = ("CompatibleAttachments", "UpgradePrototypeSIDs")
STAGES = ("vanilla", "oxa", "after_bprue", "final")
CRITICAL_HINTS = (
    "reload", "mag", "ammo", "mesh", "skeleton", "socket", "animation",
    "fittingweapon", "compatibleattachment", "attachprototype",
    "upgradeprototype", "effectprototype",
)
INDEX_PART = re.compile(r"^\[(?:\d+|\*)\]$")


def _copy_entries(group: dict | None) -> dict[str, dict]:
    if not group:
        return {}
    return {index: dict(fields) for index, fields in group["entries"].items()}


def _apply(base: dict[str, dict], writes: list[Write], root: str) -> tuple[dict[str, dict], dict]:
    if not writes:
        return {idx: dict(fields) for idx, fields in base.items()}, {
            "explicit": False, "replaced": False, "modes": [], "inherited": True,
            "removal_identity_mismatches": [],
        }
    state, meta = _apply_array_patch(base, writes, root)
    meta["inherited"] = not meta["replaced"]
    return state, meta


def _ordered_entries(state: dict[str, dict], root: str) -> list[dict]:
    def sort_key(item):
        index = item[0]
        if index.startswith("[") and index.endswith("]") and index[1:-1].isdigit():
            return (0, int(index[1:-1]))
        return (1, index)

    return [
        {"index": index, "identity": _entry_identity(root, fields), "fields": fields}
        for index, fields in sorted(state.items(), key=sort_key)
    ]


def _by_identity(entries: list[dict]) -> dict[str, list[dict]]:
    result = defaultdict(list)
    for entry in entries:
        if entry["identity"] is not None:
            result[entry["identity"]].append(entry)
    return result


def _discover_smgs(report: dict) -> list[str]:
    result = set()
    for item in report.get("three_way", []):
        additions = item.get("bprue_additions", [])
        if any("_SMGShared_" in value or "_PistolConversion" in value for value in additions):
            result.add(item["prototype"])
    return sorted(result)


def _analyse_group(prototype, root, vanilla_groups, oxa_groups, bprue_groups, compat_groups):
    key = (prototype, root)
    vanilla = _copy_entries(vanilla_groups.get(key))
    oxa, oxa_meta = _apply(vanilla, oxa_groups.get(key, []), root)
    after_bprue, bprue_meta = _apply(oxa, bprue_groups.get(key, []), root)
    final, compat_meta = _apply(after_bprue, compat_groups.get(key, []), root)
    stages = {
        "vanilla": _ordered_entries(vanilla, root),
        "oxa": _ordered_entries(oxa, root),
        "after_bprue": _ordered_entries(after_bprue, root),
        "final": _ordered_entries(final, root),
    }
    by_stage = {name: _by_identity(entries) for name, entries in stages.items()}
    findings = []

    transitions = (
        ("OXA", "vanilla", "oxa"),
        ("BPRUE", "oxa", "after_bprue"),
        ("COMPAT", "after_bprue", "final"),
    )
    for owner, before_name, after_name in transitions:
        before, after = by_stage[before_name], by_stage[after_name]
        for identity, old in before.items():
            if identity not in after:
                findings.append({
                    "severity": "CRITICAL",
                    "kind": f"{owner}_ENTRY_LOST",
                    "identity": identity,
                    "from_stage": before_name,
                    "to_stage": after_name,
                })
                continue
            old_index, new_index = old[0]["index"], after[identity][0]["index"]
            if old_index != new_index:
                findings.append({
                    "severity": "HIGH" if root == "CompatibleAttachments" else "MEDIUM",
                    "kind": f"{owner}_MOVE",
                    "identity": identity,
                    "from_index": old_index,
                    "to_index": new_index,
                })

    vanilla_ids = set(by_stage["vanilla"])
    bprue_ids = set(by_stage["after_bprue"])
    final_ids = set(by_stage["final"])
    for identity in sorted((bprue_ids - vanilla_ids) - final_ids):
        findings.append({"severity": "CRITICAL", "kind": "BPRUE_ADDITION_LOST", "identity": identity})

    # Attribute duplicates to the stage that introduced them instead of reporting
    # every inherited duplicate as a final-state problem.
    previous_dupes = set()
    for stage_name in STAGES:
        ids = [e["identity"] for e in stages[stage_name] if e["identity"] is not None]
        dupes = {x for x in ids if ids.count(x) > 1}
        introduced = sorted(dupes - previous_dupes)
        if introduced:
            findings.append({
                "severity": "HIGH",
                "kind": f"{stage_name.upper()}_DUPLICATE_INTRODUCED",
                "identities": introduced,
            })
        previous_dupes = dupes

    return {
        "prototype": prototype, "array": root,
        "metadata": {"oxa": oxa_meta, "bprue": bprue_meta, "compat": compat_meta},
        "counts": {name: len(entries) for name, entries in stages.items()},
        "stages": stages, "findings": findings,
    }


def _prototype_writes(writes: list[Write], prototype: str) -> list[Write]:
    return [w for w in writes if w.prototype == prototype]


def _materialize_flat(base: dict[str, str], writes: list[Write], source: str) -> tuple[dict[str, str], dict[str, str]]:
    """Materialize non-semantic prototype leaves.

    Semantic arrays are handled by the index-aware pipeline above. This pass catches
    every other scalar/nested leaf and records which layer last wrote it.
    """
    state = dict(base)
    provenance = {path: "vanilla" for path in state}

    # A plain top-level struct is a replacement; bpatch preserves inherited state.
    proto_nodes = [w for w in writes if w.path == "<prototype>" and w.kind == "prototype"]
    if proto_nodes and not any("bpatch" in w.modes for w in proto_nodes):
        state = {}
        provenance = {}

    for w in writes:
        if w.path == "<prototype>" or _semantic_array_root(w.path) is not None:
            continue
        if w.kind == "remove":
            prefix = w.path + "."
            for path in [p for p in state if p == w.path or p.startswith(prefix)]:
                state.pop(path, None)
                provenance.pop(path, None)
        elif w.kind == "scalar":
            state[w.path] = w.value or ""
            provenance[w.path] = source

    return state, provenance


def _vanilla_flat(writes: list[Write], prototype: str) -> tuple[dict[str, str], dict[str, str]]:
    state = {}
    provenance = {}
    for w in _prototype_writes(writes, prototype):
        if w.path == "<prototype>" or _semantic_array_root(w.path) is not None:
            continue
        if w.kind == "scalar":
            state[w.path] = w.value or ""
            provenance[w.path] = "vanilla"
    return state, provenance


def _hash_state(state: dict[str, str]) -> str:
    payload = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()[:12]


def _critical_path(path: str) -> bool:
    low = path.lower()
    return any(hint in low for hint in CRITICAL_HINTS)


def _analyse_effective(prototype: str, vanilla_writes, oxa_writes, bprue_writes, compat_writes) -> dict:
    vanilla, p0 = _vanilla_flat(vanilla_writes, prototype)
    oxa, p1 = _materialize_flat(vanilla, _prototype_writes(oxa_writes, prototype), "oxa")
    after_bprue, p2 = _materialize_flat(oxa, _prototype_writes(bprue_writes, prototype), "bprue")
    final, p3 = _materialize_flat(after_bprue, _prototype_writes(compat_writes, prototype), "compat")

    stages = {"vanilla": vanilla, "oxa": oxa, "after_bprue": after_bprue, "final": final}
    provenance = {"vanilla": p0, "oxa": p1, "after_bprue": p2, "final": p3}
    paths = sorted(set().union(*(set(s) for s in stages.values())))
    changes = []

    for path in paths:
        values = {stage: stages[stage].get(path) for stage in STAGES}
        if len(set(values.values())) == 1:
            continue
        changed_at = []
        previous = values["vanilla"]
        for stage in STAGES[1:]:
            if values[stage] != previous:
                changed_at.append(stage)
            previous = values[stage]
        changes.append({
            "path": path,
            "critical_hint": _critical_path(path),
            "values": values,
            "changed_at": changed_at,
            "final_source": provenance["final"].get(path),
        })

    compat_changes = [c for c in changes if "final" in c["changed_at"]]
    suspicious = [
        c for c in compat_changes
        if c["critical_hint"] or c["values"]["final"] is None
    ]
    return {
        "prototype": prototype,
        "counts": {stage: len(stages[stage]) for stage in STAGES},
        "hashes": {stage: _hash_state(stages[stage]) for stage in STAGES},
        "change_count": len(changes),
        "compat_change_count": len(compat_changes),
        "suspicious_compat_changes": suspicious,
        "changes": changes,
    }


def analyse(report, vanilla_root, oxa_root, bprue_root, compat_root, prototypes):
    vanilla_writes = collect_vanilla(vanilla_root)
    oxa_writes, bprue_writes, compat_writes = collect(oxa_root), collect(bprue_root), collect(compat_root)
    vanilla_groups = _semantic_arrays(vanilla_writes)
    oxa_groups = _writes_by_semantic_group(oxa_writes)
    bprue_groups = _writes_by_semantic_group(bprue_writes)
    compat_groups = _writes_by_semantic_group(compat_writes)

    groups = []
    for prototype in prototypes:
        for root in WATCH_ARRAYS:
            key = (prototype, root)
            if key in vanilla_groups or key in oxa_groups or key in bprue_groups or key in compat_groups:
                groups.append(_analyse_group(prototype, root, vanilla_groups, oxa_groups, bprue_groups, compat_groups))

    effective = [
        _analyse_effective(p, vanilla_writes, oxa_writes, bprue_writes, compat_writes)
        for p in prototypes
    ]
    severity_counts, kind_counts = defaultdict(int), defaultdict(int)
    for group in groups:
        for finding in group["findings"]:
            severity_counts[finding["severity"]] += 1
            kind_counts[finding["kind"]] += 1

    return {
        "prototypes": prototypes, "groups": groups, "effective": effective,
        "summary": {
            "prototype_count": len(prototypes), "group_count": len(groups),
            "finding_count": sum(severity_counts.values()),
            "severity_counts": dict(sorted(severity_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
            "compat_property_changes": sum(x["compat_change_count"] for x in effective),
            "suspicious_compat_property_changes": sum(len(x["suspicious_compat_changes"]) for x in effective),
        },
    }


def _short_value(value, limit=90):
    if value is None:
        return "<missing>"
    return value if len(value) <= limit else value[:limit - 3] + "..."


def _render_console(result: dict) -> str:
    """Intentionally compact. Full details live in TXT/JSON reports."""
    s = result["summary"]
    lines = [
        "BPRUE <-> OXA SMG pipeline",
        "==========================",
        f"SMGs={s['prototype_count']} groups={s['group_count']} findings={s['finding_count']} "
        f"severity={s['severity_counts']}",
        f"Compat property changes={s['compat_property_changes']} "
        f"suspicious={s['suspicious_compat_property_changes']}",
        "",
    ]
    for item in result["effective"]:
        lines.append(
            f"{item['prototype']}: hashes V={item['hashes']['vanilla']} O={item['hashes']['oxa']} "
            f"B={item['hashes']['after_bprue']} F={item['hashes']['final']} | "
            f"changes={item['change_count']} compat={item['compat_change_count']} "
            f"suspicious={len(item['suspicious_compat_changes'])}"
        )
        for change in item["suspicious_compat_changes"][:8]:
            lines.append(
                f"  ! {change['path']}: "
                f"{_short_value(change['values']['after_bprue'], 42)} -> "
                f"{_short_value(change['values']['final'], 42)}"
            )
        if len(item["suspicious_compat_changes"]) > 8:
            lines.append(f"  ... +{len(item['suspicious_compat_changes']) - 8} more in report")

    flagged_groups = [g for g in result["groups"] if g["findings"]]
    if flagged_groups:
        lines += ["", "Array findings:"]
        for group in flagged_groups:
            kinds = defaultdict(int)
            for f in group["findings"]:
                kinds[f["kind"]] += 1
            lines.append(f"  {group['prototype']} :: {group['array']} -> {dict(kinds)}")
    return "\n".join(lines) + "\n"


def _render_report(result: dict) -> str:
    lines = [_render_console(result).rstrip(), "", "PROPERTY DIFFS", "=============="]
    for item in result["effective"]:
        lines += ["", f"=== {item['prototype']} ===",
                  f"leaf counts: {item['counts']}", f"hashes: {item['hashes']}"]
        if not item["changes"]:
            lines.append("No non-array property changes.")
            continue
        for c in item["changes"]:
            marker = " !" if c["critical_hint"] else ""
            lines.append(
                f"{marker} {c['path']} | changed={','.join(c['changed_at'])} | final_source={c['final_source']}"
            )
            lines.append(
                f"    V={_short_value(c['values']['vanilla'])} | O={_short_value(c['values']['oxa'])}"
            )
            lines.append(
                f"    B={_short_value(c['values']['after_bprue'])} | F={_short_value(c['values']['final'])}"
            )

    lines += ["", "ARRAY FINDINGS", "=============="]
    for group in result["groups"]:
        if not group["findings"]:
            continue
        lines.append(
            f"{group['prototype']} :: {group['array']} counts={group['counts']} "
            f"replace(O/B/C)={group['metadata']['oxa'].get('replaced')}/"
            f"{group['metadata']['bprue'].get('replaced')}/{group['metadata']['compat'].get('replaced')}"
        )
        for f in group["findings"]:
            details = ", ".join(f"{k}={v}" for k, v in f.items() if k not in {"severity", "kind"})
            lines.append(f"  {f['severity']} {f['kind']}" + (f" :: {details}" if details else ""))
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="Simulate OXA -> BPRUE -> compat for SMGs, including complete non-array prototype provenance.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--vanilla-root", type=Path, default=ROOT / "Python/VanillaReference")
    parser.add_argument("--oxa-root", type=Path, default=DEFAULT_OXA_ROOT)
    parser.add_argument("--bprue-root", type=Path, default=DEFAULT_BPRUE_ROOT)
    parser.add_argument("--compat-root", type=Path, default=DEFAULT_COMPAT_ROOT)
    parser.add_argument("--prototype", action="append", dest="prototypes")
    parser.add_argument("--text-out", type=Path, default=DEFAULT_TEXT_OUT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    prototypes = sorted(set(args.prototypes or _discover_smgs(report)))
    if not prototypes:
        raise SystemExit("No SMG prototypes discovered. Use --prototype <SID>.")

    result = analyse(report, args.vanilla_root, args.oxa_root, args.bprue_root, args.compat_root, prototypes)
    full = _render_report(result)
    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(full, encoding="utf-8")
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(_render_console(result), end="")
    print(f"Full report: {args.text_out.relative_to(ROOT).as_posix()}")
    print(f"JSON:        {args.json_out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
