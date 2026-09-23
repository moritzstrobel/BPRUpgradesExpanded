from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from analyze_oxa_conflicts import (
    ROOT,
    SEMANTIC_ARRAYS,
    _apply_array_patch,
    _entry_identity,
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


def _copy_entries(group: dict | None) -> dict[str, dict]:
    if not group:
        return {}
    return {index: dict(fields) for index, fields in group["entries"].items()}


def _apply(base: dict[str, dict], writes: list, root: str) -> tuple[dict[str, dict], dict]:
    if not writes:
        return _copy_entries({"entries": base}), {
            "explicit": False,
            "replaced": False,
            "modes": [],
            "inherited": True,
            "removal_identity_mismatches": [],
        }
    state, meta = _apply_array_patch(base, writes, root)
    meta["inherited"] = not meta["replaced"]
    return state, meta


def _ordered_entries(state: dict[str, dict], root: str) -> list[dict]:
    def sort_key(item: tuple[str, dict]) -> tuple[int, int | str]:
        index = item[0]
        if index.startswith("[") and index.endswith("]") and index[1:-1].isdigit():
            return (0, int(index[1:-1]))
        return (1, index)

    result = []
    for index, fields in sorted(state.items(), key=sort_key):
        result.append({
            "index": index,
            "identity": _entry_identity(root, fields),
            "fields": fields,
        })
    return result


def _by_identity(entries: list[dict]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        if entry["identity"] is not None:
            result[entry["identity"]].append(entry)
    return result


def _shape(root: str, fields: dict) -> str:
    if root == "CompatibleAttachments":
        if "AttachPrototypeSID" in fields:
            return "struct"
        if "<value>" in fields:
            return "scalar"
        return "unknown"
    return "scalar" if "<value>" in fields else "unknown"


def _discover_smgs(report: dict) -> list[str]:
    result = set()
    for item in report.get("three_way", []):
        additions = item.get("bprue_additions", [])
        if any("_SMGShared_" in value or "_PistolConversion" in value for value in additions):
            result.add(item["prototype"])
    return sorted(result)


def _analyse_group(
    prototype: str,
    root: str,
    vanilla_groups: dict,
    oxa_groups: dict,
    bprue_groups: dict,
    compat_groups: dict,
) -> dict:
    key = (prototype, root)
    vanilla = _copy_entries(vanilla_groups.get(key))
    oxa, oxa_meta = _apply(vanilla, oxa_groups.get(key, []), root)

    # Actual load order: OXA -> BPRUE -> compat. BPRUE full arrays can replace
    # OXA state, and the generated compat then applies last.
    after_bprue, bprue_meta = _apply(oxa, bprue_groups.get(key, []), root)
    final, compat_meta = _apply(after_bprue, compat_groups.get(key, []), root)

    stages = {
        "vanilla": _ordered_entries(vanilla, root),
        "oxa": _ordered_entries(oxa, root),
        "after_bprue": _ordered_entries(after_bprue, root),
        "final": _ordered_entries(final, root),
    }

    oxa_by_id = _by_identity(stages["oxa"])
    final_by_id = _by_identity(stages["final"])
    bprue_by_id = _by_identity(stages["after_bprue"])

    findings = []

    if root == "CompatibleAttachments":
        for entry in stages["final"]:
            if entry["identity"] is None and _shape(root, entry["fields"]) == "scalar":
                findings.append({
                    "severity": "CRITICAL",
                    "kind": "ATTACHMENT_ENTRY_SHAPE_LOST",
                    "index": entry["index"],
                    "value": entry["fields"].get("<value>"),
                    "message": "Compat emitted a scalar where CompatibleAttachments requires a child struct.",
                })

        # The current compat generator can preserve only AttachPrototypeSID
        # identities. Check whether OXA's attachment metadata survives.
        for identity, oxa_entries in oxa_by_id.items():
            if identity not in final_by_id:
                continue
            oxa_entry = oxa_entries[0]
            final_entry = final_by_id[identity][0]
            oxa_fields = oxa_entry["fields"]
            final_fields = final_entry["fields"]
            missing_fields = sorted(
                field for field in oxa_fields
                if field != "AttachPrototypeSID" and field not in final_fields
            )
            changed_fields = sorted(
                field for field in set(oxa_fields) & set(final_fields)
                if oxa_fields[field] != final_fields[field]
            )
            if missing_fields:
                findings.append({
                    "severity": "CRITICAL",
                    "kind": "ATTACHMENT_METADATA_LOST",
                    "identity": identity,
                    "oxa_index": oxa_entry["index"],
                    "final_index": final_entry["index"],
                    "missing_fields": missing_fields,
                })
            if changed_fields:
                findings.append({
                    "severity": "HIGH",
                    "kind": "ATTACHMENT_METADATA_CHANGED",
                    "identity": identity,
                    "fields": changed_fields,
                })

    # Preserve OXA positions for identities that already existed in OXA.
    for identity, oxa_entries in oxa_by_id.items():
        if identity not in final_by_id:
            findings.append({
                "severity": "CRITICAL",
                "kind": "OXA_ENTRY_LOST",
                "identity": identity,
                "oxa_index": oxa_entries[0]["index"],
            })
            continue
        old_index = oxa_entries[0]["index"]
        new_index = final_by_id[identity][0]["index"]
        if old_index != new_index:
            findings.append({
                "severity": "HIGH" if root == "CompatibleAttachments" else "MEDIUM",
                "kind": "EXISTING_ENTRY_MOVED",
                "identity": identity,
                "oxa_index": old_index,
                "final_index": new_index,
            })

    # BPRUE additions should survive the final compat state.
    vanilla_ids = set(_by_identity(stages["vanilla"]))
    bprue_ids = set(bprue_by_id)
    final_ids = set(final_by_id)
    for identity in sorted((bprue_ids - vanilla_ids) - final_ids):
        findings.append({
            "severity": "CRITICAL",
            "kind": "BPRUE_ADDITION_LOST",
            "identity": identity,
        })

    final_identities = [entry["identity"] for entry in stages["final"] if entry["identity"] is not None]
    duplicates = sorted({value for value in final_identities if final_identities.count(value) > 1})
    if duplicates:
        findings.append({
            "severity": "HIGH",
            "kind": "DUPLICATE_IDENTITIES",
            "identities": duplicates,
        })

    return {
        "prototype": prototype,
        "array": root,
        "metadata": {
            "oxa": oxa_meta,
            "bprue": bprue_meta,
            "compat": compat_meta,
        },
        "counts": {name: len(entries) for name, entries in stages.items()},
        "stages": stages,
        "findings": findings,
    }


def analyse(report: dict, vanilla_root: Path, oxa_root: Path, bprue_root: Path, compat_root: Path, prototypes: list[str]) -> dict:
    vanilla_writes = collect_vanilla(vanilla_root)
    oxa_writes = collect(oxa_root)
    bprue_writes = collect(bprue_root)
    compat_writes = collect(compat_root)

    vanilla_groups = _semantic_arrays(vanilla_writes)
    oxa_groups = _writes_by_semantic_group(oxa_writes)
    bprue_groups = _writes_by_semantic_group(bprue_writes)
    compat_groups = _writes_by_semantic_group(compat_writes)

    groups = []
    for prototype in prototypes:
        for root in WATCH_ARRAYS:
            key = (prototype, root)
            if key not in vanilla_groups and key not in oxa_groups and key not in bprue_groups and key not in compat_groups:
                continue
            groups.append(_analyse_group(
                prototype, root, vanilla_groups, oxa_groups, bprue_groups, compat_groups
            ))

    severity_counts = defaultdict(int)
    kind_counts = defaultdict(int)
    for group in groups:
        for finding in group["findings"]:
            severity_counts[finding["severity"]] += 1
            kind_counts[finding["kind"]] += 1

    return {
        "prototypes": prototypes,
        "groups": groups,
        "summary": {
            "prototype_count": len(prototypes),
            "group_count": len(groups),
            "finding_count": sum(severity_counts.values()),
            "severity_counts": dict(sorted(severity_counts.items())),
            "kind_counts": dict(sorted(kind_counts.items())),
        },
    }


def _render(result: dict) -> str:
    lines = [
        "BPRUE <-> OXA SMG pipeline analysis",
        "==================================",
        f"SMGs: {', '.join(result['prototypes'])}",
        f"Groups: {result['summary']['group_count']}",
        f"Findings: {result['summary']['finding_count']}",
        f"Severity: {result['summary']['severity_counts']}",
        f"Kinds: {result['summary']['kind_counts']}",
        "",
    ]

    for group in result["groups"]:
        lines.append(f"=== {group['prototype']} :: {group['array']} ===")
        lines.append(f"counts: {group['counts']}")
        lines.append(
            "semantics: "
            f"OXA={group['metadata']['oxa'].get('modes', [])}/replace={group['metadata']['oxa'].get('replaced')} | "
            f"BPRUE={group['metadata']['bprue'].get('modes', [])}/replace={group['metadata']['bprue'].get('replaced')} | "
            f"Compat={group['metadata']['compat'].get('modes', [])}/replace={group['metadata']['compat'].get('replaced')}"
        )

        if not group["findings"]:
            lines.append("OK: no suspicious structural/index changes detected")
        else:
            for finding in group["findings"]:
                details = ", ".join(
                    f"{key}={value}"
                    for key, value in finding.items()
                    if key not in {"severity", "kind", "message"}
                )
                line = f"{finding['severity']:8} {finding['kind']}"
                if details:
                    line += f" :: {details}"
                if finding.get("message"):
                    line += f" -- {finding['message']}"
                lines.append(line)

        lines.append("")
        for stage_name in ("vanilla", "oxa", "after_bprue", "final"):
            lines.append(f"  {stage_name}:")
            for entry in group["stages"][stage_name]:
                shape = _shape(group["array"], entry["fields"])
                lines.append(
                    f"    {entry['index']:>5}  {entry['identity'] or '<NO ID>'}  shape={shape}"
                )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate the OXA -> BPRUE -> OXA compat pipeline for BPRUE SMGs and flag structural/index hazards."
    )
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

    result = analyse(
        report,
        args.vanilla_root,
        args.oxa_root,
        args.bprue_root,
        args.compat_root,
        prototypes,
    )

    rendered = _render(result)
    print(rendered, end="")

    args.text_out.parent.mkdir(parents=True, exist_ok=True)
    args.text_out.write_text(rendered, encoding="utf-8")
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"Wrote {args.text_out.relative_to(ROOT).as_posix()}")
    print(f"Wrote {args.json_out.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
