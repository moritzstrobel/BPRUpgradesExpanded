from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "Python/Analysis/Reports/oxa_conflicts.json"
DEFAULT_COMPAT = ROOT / "Compat/OXA/GameLite"

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
    groups: dict[tuple[str, str], dict] = {}
    errors: list[str] = []

    for path in sorted(root.rglob("*.cfg")):
        rel = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        prototype = None
        array = None
        entries: list[tuple[int, str]] = []

        def finish_array() -> None:
            nonlocal array, entries
            if prototype is None or array is None:
                return
            key = (prototype, array)
            if key in groups:
                errors.append(f"duplicate group {prototype} :: {array} ({groups[key]['source']} and {rel})")
            indexes = [i for i, _ in entries]
            if indexes != list(range(len(entries))):
                errors.append(f"non-contiguous indexes {prototype} :: {array} in {rel}: {indexes}")
            values = [v for _, v in sorted(entries)]
            if len(values) != len(set(values)):
                errors.append(f"duplicate values {prototype} :: {array} in {rel}")
            groups[key] = {"values": values, "source": rel}
            array = None
            entries = []

        for lineno, line in enumerate(lines, 1):
            if array is not None:
                m = ENTRY_RE.match(line)
                if m:
                    entries.append((int(m.group(1)), m.group(2)))
                    continue
                if END_RE.match(line):
                    finish_array()
                    continue
                if line.strip() and not line.lstrip().startswith("//"):
                    errors.append(f"unexpected array syntax {rel}:{lineno}: {line.strip()}")
                continue

            m = PROTO_RE.match(line)
            if m:
                prototype = m.group(1).strip()
                continue

            if prototype is not None:
                m = ARRAY_RE.match(line)
                if m:
                    array = m.group(1)
                    entries = []
                    continue
                if END_RE.match(line):
                    prototype = None

        if array is not None:
            errors.append(f"unterminated array in {rel}")
            finish_array()

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


def validate(report: dict, compat_root: Path) -> dict:
    actual, syntax_errors = parse_compat(compat_root)
    expected, unresolved = expected_groups(report)

    missing = []
    unexpected = []
    content_mismatches = []
    ordering_notes = []
    scope_errors = []

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

    for key, value in actual.items():
        if key not in expected:
            unexpected.append({
                "prototype": key[0],
                "array": key[1],
                "source": value["source"],
                "reason": "unresolved OXA group" if key in unresolved else "not required by analyzer candidate",
            })

    return {
        "valid": not (syntax_errors or missing or unexpected or content_mismatches or scope_errors),
        "summary": {
            "expected_groups": len(expected),
            "actual_groups": len(actual),
            "syntax_errors": len(syntax_errors),
            "missing_groups": len(missing),
            "unexpected_groups": len(unexpected),
            "content_mismatches": len(content_mismatches),
            "scope_errors": len(scope_errors),
            "ordering_notes": len(ordering_notes),
            "intentionally_unresolved_groups": len(unresolved),
        },
        "syntax_errors": syntax_errors,
        "missing_groups": missing,
        "unexpected_groups": unexpected,
        "content_mismatches": content_mismatches,
        "scope_errors": scope_errors,
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

    for section in ("syntax_errors", "missing_groups", "unexpected_groups", "content_mismatches", "scope_errors"):
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
