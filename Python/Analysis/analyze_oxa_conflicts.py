from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OXA_ROOT = ROOT / "Python/VanillaReference/OxaData"
DEFAULT_BPRUE_ROOT = ROOT / "GameLite"
DEFAULT_REPORT_DIR = ROOT / "Python/Analysis/Reports"

STRUCT_BEGIN = re.compile(r"^\s*([^\s:]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?")
STRUCT_END = re.compile(r"^\s*struct\.end\s*$")
SCALAR = re.compile(r"^\s*([^\s=]+)\s*=\s*(.*?)\s*$")
REMOVE = re.compile(r"^\s*([^\s:]+)\s*:\s*removenode\s*$")


@dataclass
class Write:
    source: str
    prototype: str
    path: str
    kind: str
    value: str | None = None
    modes: tuple[str, ...] = field(default_factory=tuple)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def modes(raw: str | None) -> tuple[str, ...]:
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(";") if part.strip())


def parse_cfg(path: Path) -> list[Write]:
    writes: list[Write] = []
    stack: list[tuple[str, tuple[str, ...]]] = []
    prototype: str | None = None

    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.split("//", 1)[0].rstrip()
        if not line.strip():
            continue

        match = STRUCT_BEGIN.match(line)
        if match:
            name, raw_modes = match.groups()
            node_modes = modes(raw_modes)
            if not stack:
                prototype = name
                stack.append((name, node_modes))
                writes.append(Write(rel(path), prototype, "<prototype>", "prototype", None, node_modes))
            else:
                stack.append((name, node_modes))
                node_path = ".".join(part[0] for part in stack[1:])
                writes.append(Write(rel(path), prototype or "", node_path, "struct", None, node_modes))
            continue

        if STRUCT_END.match(line):
            if stack:
                stack.pop()
                if not stack:
                    prototype = None
            continue

        if not stack or prototype is None:
            continue

        match = REMOVE.match(line)
        if match:
            node_path = ".".join([part[0] for part in stack[1:]] + [match.group(1)])
            writes.append(Write(rel(path), prototype, node_path, "remove", None, ()))
            continue

        match = SCALAR.match(line)
        if match:
            name, value = match.groups()
            node_path = ".".join([part[0] for part in stack[1:]] + [name])
            writes.append(Write(rel(path), prototype, node_path, "scalar", value.strip(), ()))

    return writes


def collect(root: Path) -> list[Write]:
    if not root.exists():
        raise FileNotFoundError(root)
    writes: list[Write] = []
    for path in sorted(root.rglob("*.cfg")):
        writes.extend(parse_cfg(path))
    return writes


def index(writes: list[Write]) -> dict[tuple[str, str], list[Write]]:
    result: dict[tuple[str, str], list[Write]] = defaultdict(list)
    for write in writes:
        result[(write.prototype, write.path)].append(write)
    return result


def classify(a: Write, b: Write) -> str:
    if a.path == "<prototype>":
        return "PROTOTYPE_OVERLAP"
    if a.kind == "remove" or b.kind == "remove":
        return "CONFLICT"
    if a.kind == "scalar" and b.kind == "scalar":
        return "SAME_VALUE" if a.value == b.value else "CONFLICT"
    if a.kind == "struct" or b.kind == "struct":
        return "STRUCTURAL"
    return "OVERLAP"



INDEX_RE = re.compile(r"^\[(?:\d+|\*)\]$")
SEMANTIC_ARRAYS = {
    "UpgradePrototypeSIDs": None,
    "FittingWeaponsSIDs": None,
    "CompatibleAttachments": "AttachPrototypeSID",
    "AttachPrototypeSIDs": None,
    "EffectPrototypeSIDs": None,
    "InterchangeableUpgradePrototypeSIDs": None,
    "RequiredUpgradeIDs": None,
}


def _semantic_array_root(path: str) -> str | None:
    top = path.split(".", 1)[0]
    return top if top in SEMANTIC_ARRAYS else None


def _array_entry_path(path: str, root: str) -> tuple[str | None, str | None]:
    parts = path.split(".")
    if not parts or parts[0] != root or len(parts) < 2 or not INDEX_RE.match(parts[1]):
        return None, None
    return parts[1], ".".join(parts[2:]) or None


def _semantic_arrays(writes: list[Write]) -> dict[tuple[str, str], dict]:
    groups: dict[tuple[str, str], dict] = {}
    for w in writes:
        root = _semantic_array_root(w.path)
        if root is None:
            continue
        key = (w.prototype, root)
        group = groups.setdefault(key, {"sources": set(), "entries": defaultdict(dict), "struct_modes": set()})
        group["sources"].add(w.source)
        if w.path == root and w.kind == "struct":
            group["struct_modes"].update(w.modes)
            continue
        index, child = _array_entry_path(w.path, root)
        if index is None:
            continue
        entry = group["entries"][index]
        if w.kind == "scalar":
            entry[child or "<value>"] = w.value
        elif w.kind == "remove":
            entry[child or "<remove>"] = "<removed>"
    return groups


def _entry_identity(root: str, fields: dict) -> str | None:
    identity_field = SEMANTIC_ARRAYS[root]
    if identity_field:
        return fields.get(identity_field)
    return fields.get("<value>")


def _semantic_compare(bprue: list[Write], oxa: list[Write]) -> list[dict]:
    left, right = _semantic_arrays(bprue), _semantic_arrays(oxa)
    results = []
    for prototype, root in sorted(set(left) & set(right)):
        a, b = left[(prototype, root)], right[(prototype, root)]
        a_by_id, b_by_id = defaultdict(list), defaultdict(list)
        for index, fields in a["entries"].items():
            identity = _entry_identity(root, fields)
            if identity is not None:
                a_by_id[identity].append({"index": index, "fields": fields})
        for index, fields in b["entries"].items():
            identity = _entry_identity(root, fields)
            if identity is not None:
                b_by_id[identity].append({"index": index, "fields": fields})

        a_ids, b_ids = set(a_by_id), set(b_by_id)
        index_collisions = []
        for index in sorted(set(a["entries"]) & set(b["entries"])):
            ai = _entry_identity(root, a["entries"][index])
            bi = _entry_identity(root, b["entries"][index])
            if ai is not None and bi is not None and ai != bi:
                index_collisions.append({"index": index, "bprue": ai, "oxa": bi})

        field_conflicts = []
        for identity in sorted(a_ids & b_ids):
            for ae in a_by_id[identity]:
                for be in b_by_id[identity]:
                    for field_name in sorted(set(ae["fields"]) & set(be["fields"])):
                        av, bv = ae["fields"][field_name], be["fields"][field_name]
                        if av != bv:
                            field_conflicts.append({
                                "identity": identity, "field": field_name,
                                "bprue": av, "oxa": bv,
                                "bprue_index": ae["index"], "oxa_index": be["index"],
                            })

        if field_conflicts:
            severity = "CONTENT_CONFLICT"
        elif index_collisions:
            severity = "INDEX_COLLISION"
        elif a_ids == b_ids:
            severity = "SAME_CONTENT"
        else:
            severity = "MERGE_REQUIRED"

        results.append({
            "severity": severity,
            "prototype": prototype,
            "array": root,
            "bprue_sources": sorted(a["sources"]),
            "oxa_sources": sorted(b["sources"]),
            "bprue_modes": sorted(a["struct_modes"]),
            "oxa_modes": sorted(b["struct_modes"]),
            "common": sorted(a_ids & b_ids),
            "bprue_only": sorted(a_ids - b_ids),
            "oxa_only": sorted(b_ids - a_ids),
            "index_collisions": index_collisions,
            "field_conflicts": field_conflicts,
        })
    return results


def _semantic_summary(items: list[dict]) -> dict:
    counts = defaultdict(int)
    arrays = defaultdict(int)
    for item in items:
        counts[item["severity"]] += 1
        arrays[item["array"]] += 1
    return {
        "groups": len(items),
        "severity_counts": dict(sorted(counts.items())),
        "array_counts": dict(sorted(arrays.items())),
    }


def analyze(bprue: list[Write], oxa: list[Write]) -> dict:
    left, right = index(bprue), index(oxa)
    overlaps = []
    for key in sorted(set(left) & set(right)):
        for a in left[key]:
            for b in right[key]:
                severity = classify(a, b)
                overlaps.append({
                    "severity": severity,
                    "prototype": key[0],
                    "path": key[1],
                    "bprue": {"source": a.source, "kind": a.kind, "value": a.value, "modes": list(a.modes)},
                    "oxa": {"source": b.source, "kind": b.kind, "value": b.value, "modes": list(b.modes)},
                })

    bprue_prototypes = {w.prototype for w in bprue}
    oxa_prototypes = {w.prototype for w in oxa}
    counts = defaultdict(int)
    for item in overlaps:
        counts[item["severity"]] += 1

    oxa_sources = defaultdict(set)
    for w in oxa:
        oxa_sources[w.prototype].add(w.source)

    semantic = _semantic_compare(bprue, oxa)

    return {
        "summary": {
            "bprue_cfg_writes": len(bprue),
            "oxa_cfg_writes": len(oxa),
            "bprue_prototypes": len(bprue_prototypes),
            "oxa_prototypes": len(oxa_prototypes),
            "overlapping_prototypes": len(bprue_prototypes & oxa_prototypes),
            "overlapping_paths": len(set(left) & set(right)),
            "overlap_records": len(overlaps),
            "severity_counts": dict(sorted(counts.items())),
            "oxa_multi_source_prototypes": sum(1 for sources in oxa_sources.values() if len(sources) > 1),
            "semantic_arrays": _semantic_summary(semantic),
        },
        "semantic_arrays": semantic,
        "overlaps": overlaps,
        "oxa_multi_source": [
            {"prototype": sid, "sources": sorted(sources)}
            for sid, sources in sorted(oxa_sources.items())
            if len(sources) > 1
        ],
    }


def render_text(report: dict) -> str:
    summary = report["summary"]
    lines = ["BPRUE <-> OXA CFG conflict analysis", "=" * 36, ""]
    for key, value in summary.items():
        if key != "severity_counts":
            lines.append(f"{key}: {value}")
    lines.append("severity_counts:")
    for key, value in summary["severity_counts"].items():
        lines.append(f"  {key}: {value}")

    if report.get("semantic_arrays"):
        lines += ["", "Semantic array conflicts", "------------------------"]
        for item in report["semantic_arrays"]:
            lines += [
                f"[{item['severity']}] {item['prototype']} :: {item['array']}",
                f"  common={len(item['common'])} bprue_only={len(item['bprue_only'])} oxa_only={len(item['oxa_only'])}",
                f"  index_collisions={len(item['index_collisions'])} field_conflicts={len(item['field_conflicts'])}",
            ]
            if item["bprue_only"]:
                lines.append("  BPRUE only: " + ", ".join(item["bprue_only"]))
            if item["oxa_only"]:
                lines.append("  OXA only:   " + ", ".join(item["oxa_only"]))
            for collision in item["index_collisions"]:
                lines.append(f"  INDEX {collision['index']}: BPRUE={collision['bprue']} OXA={collision['oxa']}")
            for conflict in item["field_conflicts"]:
                lines.append(
                    f"  FIELD {conflict['identity']}.{conflict['field']}: "
                    f"BPRUE={conflict['bprue']} OXA={conflict['oxa']}"
                )
            lines.append("")

    lines += ["", "Raw overlaps", "------------"]
    for item in report["overlaps"]:
        lines += [
            f"[{item['severity']}] {item['prototype']} :: {item['path']}",
            f"  BPRUE: {item['bprue']['source']}",
            f"         kind={item['bprue']['kind']} value={item['bprue']['value']!r} modes={item['bprue']['modes']}",
            f"  OXA:   {item['oxa']['source']}",
            f"         kind={item['oxa']['kind']} value={item['oxa']['value']!r} modes={item['oxa']['modes']}",
            "",
        ]

    lines += ["OXA prototypes patched from multiple files", "-----------------------------------------"]
    for item in report["oxa_multi_source"]:
        lines.append(item["prototype"])
        for source in item["sources"]:
            lines.append(f"  - {source}")
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare BPRUE and OXA CFG writes by prototype and property path.")
    parser.add_argument("--bprue-root", type=Path, default=DEFAULT_BPRUE_ROOT)
    parser.add_argument("--oxa-root", type=Path, default=DEFAULT_OXA_ROOT)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    args = parser.parse_args()

    bprue = collect(args.bprue_root)
    oxa = collect(args.oxa_root)
    report = analyze(bprue, oxa)

    args.report_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.report_dir / "oxa_conflicts.json"
    text_path = args.report_dir / "oxa_conflicts.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(render_text(report), encoding="utf-8")

    print(render_text({"summary": report["summary"], "semantic_arrays": report["semantic_arrays"], "overlaps": [], "oxa_multi_source": []}).rstrip())
    print(f"\nWrote {rel(json_path)}")
    print(f"Wrote {rel(text_path)}")


if __name__ == "__main__":
    main()
