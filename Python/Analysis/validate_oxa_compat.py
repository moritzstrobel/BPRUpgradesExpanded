from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from analyze_oxa_conflicts import collect, _entry_identity, _semantic_arrays

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "Python/Analysis/Reports/oxa_conflicts.json"
DEFAULT_COMPAT = ROOT / "Compat/OXA/GameLite"
DEFAULT_VANILLA = ROOT / "Python/VanillaReference"

PROTO_RE = re.compile(r"^\s*([^\s/][^:]*)\s*:\s*struct\.begin\s*\{bpatch\}")
ARRAY_RE = re.compile(r"^\s*(UpgradePrototypeSIDs|FittingWeaponsSIDs|CompatibleAttachments)\s*:\s*struct\.begin(?!\s*\{bpatch\})")
ENTRY_RE = re.compile(r"^\s*\[(\d+)\]\s*=\s*(\S+)\s*$")
END_RE = re.compile(r"^\s*struct\.end\s*$")

ARRAY_PATHS = {
    "UpgradePrototypeSIDs": "WeaponData/WeaponGeneralSetupPrototypes",
    "CompatibleAttachments": "WeaponData/WeaponGeneralSetupPrototypes",
    "FittingWeaponsSIDs": "ItemPrototypes/AttachPrototypes",
}


def parse_compat(root: Path) -> tuple[dict[tuple[str, str], dict], list[str]]:
    """Parse generated compat arrays with the same CFG parser as the analyzer.

    This is important for CompatibleAttachments: entries are child structs with
    metadata, not scalar SID values.
    """
    groups = {}
    errors = []
    try:
        parsed = _semantic_arrays(collect(root))
    except Exception as exc:
        return {}, [f"failed to parse compat CFGs: {exc}"]

    for key, group in parsed.items():
        prototype, array = key
        if array not in ARRAY_PATHS:
            continue
        ordered = sorted(
            group["entries"].items(),
            key=lambda pair: int(pair[0][1:-1]) if pair[0][1:-1].isdigit() else 10**9,
        )
        values = []
        entries = []
        for index, fields in ordered:
            identity = _entry_identity(array, fields)
            if identity is None:
                errors.append(f"missing identity {prototype} :: {array} {index}")
                continue
            values.append(identity)
            entries.append({"index": index, "identity": identity, "fields": dict(fields)})

        numeric = [int(e["index"][1:-1]) for e in entries if e["index"][1:-1].isdigit()]
        if numeric != list(range(len(numeric))):
            errors.append(f"non-contiguous indexes {prototype} :: {array}: {numeric}")
        if len(values) != len(set(values)):
            errors.append(f"duplicate values {prototype} :: {array}")

        sources = sorted(group.get("sources", []))
        groups[key] = {
            "values": values,
            "entries": entries,
            "source": sources[0] if sources else "<unknown>",
        }
    return groups, errors


def expected_groups(report: dict) -> tuple[dict[tuple[str, str], dict], set[tuple[str, str]]]:
    unresolved = {
        (item["prototype"], item["array"])
        for item in report.get("removal_identity_mismatches", {}).get("records", [])
        if item.get("resolution") == "unresolved_comment_identity"
    }

    expected = {}
    for item in report["three_way"]:
        key = (item["prototype"], item["array"])
        if item["array"] not in ARRAY_PATHS or not item["bprue_additions"] or key in unresolved:
            continue
        expected[key] = item
    return expected, unresolved


def _apply_against_vanilla(report: dict, actual: dict[tuple[str, str], dict]) -> list[dict]:
    """Simulate the generated full-array patch against the analyzer's Vanilla state.

    The generated arrays intentionally omit {bpatch}, so applying them replaces
    the inherited Vanilla array. The resulting effective state must therefore be
    exactly the generated values and exactly the analyzer compatibility candidate.
    """
    analyzer = {
        (item["prototype"], item["array"]): item
        for item in report["three_way"]
        if item["array"] in ARRAY_PATHS
    }
    failures = []

    for key, patch in actual.items():
        item = analyzer.get(key)
        if item is None:
            continue

        vanilla = item["vanilla"]
        generated = patch["values"]

        # Runtime semantics for "Array : struct.begin" inside a prototype bpatch:
        # replace the inherited array, rather than append/index-patch it.
        effective = list(generated)
        expected = item["compatibility_candidate"]

        if effective != expected:
            failures.append({
                "prototype": key[0],
                "array": key[1],
                "vanilla_count": len(vanilla),
                "generated_count": len(generated),
                "effective_count": len(effective),
                "expected_count": len(expected),
                "missing_values": sorted(set(expected) - set(effective)),
                "extra_values": sorted(set(effective) - set(expected)),
                "source": patch["source"],
            })

    return failures


def validate(report: dict, compat_root: Path) -> dict:
    actual, syntax_errors = parse_compat(compat_root)
    expected, unresolved = expected_groups(report)

    missing = []
    unexpected = []
    content_mismatches = []
    ordering_notes = []
    scope_errors = []
    effective_state_failures = []

    for key, item in expected.items():
        prototype, array = key
        if key not in actual:
            missing.append({"prototype": prototype, "array": array})
            continue

        got = actual[key]["values"]
        want = item["compatibility_candidate"]
        got_set, want_set = set(got), set(want)

        if got_set != want_set or len(got) != len(want):
            content_mismatches.append({
                "prototype": prototype,
                "array": array,
                "missing_values": sorted(want_set - got_set),
                "extra_values": sorted(got_set - want_set),
                "expected_count": len(want),
                "actual_count": len(got),
                "source": actual[key]["source"],
            })
        elif got != want:
            ordering_notes.append({
                "prototype": prototype,
                "array": array,
                "source": actual[key]["source"],
            })

        source = actual[key]["source"]
        expected_suffix = ARRAY_PATHS[array] + "/"
        if expected_suffix not in source:
            scope_errors.append({
                "prototype": prototype,
                "array": array,
                "source": source,
                "expected_path_fragment": expected_suffix,
            })

    effective_state_failures = _apply_against_vanilla(report, actual)
    for key, value in actual.items():
        if key not in expected:
            unexpected.append({
                "prototype": key[0],
                "array": key[1],
                "source": value["source"],
                "reason": "unresolved OXA group" if key in unresolved else "not required by analyzer candidate",
            })

    return {
        "valid": not (syntax_errors or missing or unexpected or content_mismatches or scope_errors or effective_state_failures),
        "summary": {
            "expected_groups": len(expected),
            "actual_groups": len(actual),
            "syntax_errors": len(syntax_errors),
            "missing_groups": len(missing),
            "unexpected_groups": len(unexpected),
            "content_mismatches": len(content_mismatches),
            "scope_errors": len(scope_errors),
            "effective_state_failures": len(effective_state_failures),
            "ordering_notes": len(ordering_notes),
            "intentionally_unresolved_groups": len(unresolved),
        },
        "syntax_errors": syntax_errors,
        "missing_groups": missing,
        "unexpected_groups": unexpected,
        "content_mismatches": content_mismatches,
        "scope_errors": scope_errors,        "effective_state_failures": effective_state_failures,
        "ordering_notes": ordering_notes,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate generated BPRUE/OXA compatibility CFGs against the analyzer candidate."
    )
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--compat-root", type=Path, default=DEFAULT_COMPAT)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate(report, args.compat_root)

    print("BPRUE <-> OXA compatibility validation")
    print("======================================")
    for key, value in result["summary"].items():
        print(f"{key}: {value}")

    for section in ("syntax_errors", "missing_groups", "unexpected_groups", "content_mismatches", "scope_errors", "effective_state_failures"):
        items = result[section]
        if items:
            print(f"\n{section}:")
            for item in items:
                print(f"  {item}")

    if result["ordering_notes"]:
        print("\nordering_notes:")
        for item in result["ordering_notes"][:20]:
            print(f"  {item['prototype']} :: {item['array']} ({item['source']})")
        if len(result["ordering_notes"]) > 20:
            print(f"  ... {len(result['ordering_notes']) - 20} more")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\nVALID" if result["valid"] else "\nINVALID")
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
