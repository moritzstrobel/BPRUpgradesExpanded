from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


STRUCT_START_RE = re.compile(r"^\s*([^\s:]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?")
STRUCT_END_RE = re.compile(r"^\s*struct\.end\s*$")
ASSIGN_RE = re.compile(r"^\s*([^=]+?)\s*=\s*(.*?)\s*(?://.*)?$")
ARRAY_RE = re.compile(r"^\s*\[(\d+|\*)\]\s*=\s*([^\s/]+)")
REFKEY_RE = re.compile(r"(?:^|;)\s*refkey\s*=\s*([^;]+)")


def strip_comments(text: str) -> str:
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


def parse_top_level_structs(path: Path) -> dict[str, dict]:
    """Parse enough CFG structure for prototype/effect analysis.

    Keeps scalar fields and direct indexed arrays. Nested non-array structs are
    intentionally ignored; the analyzer only needs prototype metadata and SID lists.
    """
    text = strip_comments(path.read_text(encoding="utf-8-sig", errors="replace"))
    result: dict[str, dict] = {}
    current: dict | None = None
    depth = 0
    array_name: str | None = None
    array_depth = -1

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        start = STRUCT_START_RE.match(line)
        if start:
            name, attrs = start.groups()
            if depth == 0:
                refkey = None
                if attrs:
                    match = REFKEY_RE.search(attrs)
                    refkey = match.group(1).strip() if match else None
                current = {"name": name, "refkey": refkey, "fields": {}, "arrays": {}}
                result[name] = current
            elif current is not None and depth == 1:
                array_name = name
                array_depth = depth + 1
                current["arrays"].setdefault(array_name, [])
            depth += 1
            continue

        if STRUCT_END_RE.match(line):
            if current is not None and depth == array_depth:
                array_name = None
                array_depth = -1
            depth -= 1
            if depth == 0:
                current = None
            continue

        if current is None:
            continue

        if array_name is not None and depth == array_depth:
            match = ARRAY_RE.match(line)
            if match:
                current["arrays"][array_name].append(match.group(2).strip())
            continue

        if depth == 1:
            match = ASSIGN_RE.match(line)
            if match:
                key, value = match.groups()
                current["fields"][key.strip()] = value.strip()

    return result


def resolve_artifact(name: str, prototypes: dict[str, dict], cache: dict[str, dict], stack: set[str]) -> dict:
    if name in cache:
        return cache[name]
    if name in stack:
        raise ValueError(f"Cyclic artifact refkey chain detected at {name}")
    proto = prototypes[name]
    stack.add(name)

    fields: dict[str, str] = {}
    arrays: dict[str, list[str]] = {}
    parent = proto.get("refkey")
    if parent and parent in prototypes:
        resolved_parent = resolve_artifact(parent, prototypes, cache, stack)
        fields.update(resolved_parent["fields"])
        arrays.update({k: list(v) for k, v in resolved_parent["arrays"].items()})

    fields.update(proto["fields"])
    arrays.update({k: list(v) for k, v in proto["arrays"].items()})
    stack.remove(name)

    resolved = {"fields": fields, "arrays": arrays}
    cache[name] = resolved
    return resolved


def effect_summary(proto: dict | None) -> dict | None:
    if proto is None:
        return None
    fields = proto["fields"]
    return {
        "type": fields.get("Type"),
        "value_min": fields.get("ValueMin"),
        "value_max": fields.get("ValueMax"),
        "positive": fields.get("Positive"),
        "localization_sid": fields.get("LocalizationSID"),
        "text": fields.get("Text"),
        "permanent": fields.get("bIsPermanent"),
        "show_upgrade_effect": fields.get("ShowUpgradeEffect"),
        "show_upgrade_effect_value": fields.get("ShowUpgradeEffectValue"),
    }


def discover_effect_files(root: Path, explicit: list[Path]) -> list[Path]:
    files = [p for p in explicit if p.exists()]
    if root.exists():
        files.extend(root.rglob("*EffectPrototypes*.cfg"))
    return sorted(set(files))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory Vanilla artifact effects and resolve their EffectPrototypes.")
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("Python/VanillaReference/ArtifactPrototypes.cfg"),
        help="ArtifactPrototypes.cfg path",
    )
    parser.add_argument(
        "--effect-root",
        type=Path,
        default=Path("Python/VanillaReference"),
        help="Root recursively searched for *EffectPrototypes*.cfg",
    )
    parser.add_argument(
        "--effects",
        type=Path,
        nargs="*",
        default=[],
        help="Additional EffectPrototype CFG files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("Python/AnalysisArmor/Reports/artifact_effect_analysis.json"),
    )
    args = parser.parse_args()

    if not args.artifacts.exists():
        raise SystemExit(f"Artifact file not found: {args.artifacts}")

    artifact_prototypes = parse_top_level_structs(args.artifacts)
    effect_files = discover_effect_files(args.effect_root, args.effects)

    effects: dict[str, dict] = {}
    effect_sources: dict[str, str] = {}
    for path in effect_files:
        for sid, proto in parse_top_level_structs(path).items():
            effects[sid] = proto
            effect_sources[sid] = path.as_posix()

    resolved_cache: dict[str, dict] = {}
    artifacts: list[dict] = []
    usage: defaultdict[str, list[str]] = defaultdict(list)
    unresolved: Counter[str] = Counter()
    effect_type_counts: Counter[str] = Counter()
    effect_sid_counts: Counter[str] = Counter()

    for name, proto in artifact_prototypes.items():
        resolved = resolve_artifact(name, artifact_prototypes, resolved_cache, set())
        fields = resolved["fields"]
        if fields.get("Type") != "EItemType::Artifact":
            continue

        # Fake artifacts inherit the real artifact's equipped effects but are not
        # useful candidates for armor-module mechanics.
        is_fake = fields.get("ArtifactType") == "EArtifactType::Fake"
        effect_sids = [sid for sid in resolved["arrays"].get("EffectPrototypeSIDs", []) if sid != "empty"]

        effect_rows = []
        for sid in effect_sids:
            effect_sid_counts[sid] += 1
            usage[sid].append(fields.get("SID", name))
            proto_effect = effects.get(sid)
            summary = effect_summary(proto_effect)
            if summary is None:
                unresolved[sid] += 1
            elif summary.get("type"):
                effect_type_counts[summary["type"]] += 1
            effect_rows.append({
                "sid": sid,
                "source": effect_sources.get(sid),
                **(summary or {"type": None, "value_min": None, "value_max": None, "positive": None,
                               "localization_sid": None, "text": None, "permanent": None,
                               "show_upgrade_effect": None, "show_upgrade_effect_value": None}),
            })

        artifacts.append({
            "sid": fields.get("SID", name),
            "prototype": name,
            "refkey": proto.get("refkey"),
            "artifact_type": fields.get("ArtifactType"),
            "element_type": fields.get("AnomalyElementType"),
            "rarity": fields.get("Rarity"),
            "weight": fields.get("Weight"),
            "cost": fields.get("Cost"),
            "fake": is_fake,
            "effects": effect_rows,
        })

    real_artifacts = [a for a in artifacts if not a["fake"] and a["sid"] != "TemplateArtifact"]
    real_effect_sids = Counter(
        effect["sid"] for artifact in real_artifacts for effect in artifact["effects"]
    )
    real_effect_types = Counter(
        effect["type"] for artifact in real_artifacts for effect in artifact["effects"] if effect["type"]
    )

    report = {
        "summary": {
            "artifact_prototypes": len(artifact_prototypes),
            "artifacts_resolved": len(artifacts),
            "real_artifacts": len(real_artifacts),
            "effect_files_scanned": len(effect_files),
            "effect_prototypes_loaded": len(effects),
            "unique_effect_sids_used_by_real_artifacts": len(real_effect_sids),
            "unresolved_effect_sids": len([sid for sid in real_effect_sids if sid not in effects]),
        },
        "effect_type_usage_real_artifacts": dict(real_effect_types.most_common()),
        "effect_sid_usage_real_artifacts": dict(real_effect_sids.most_common()),
        "unresolved_effects": {
            sid: {"uses": count, "artifacts": usage[sid]}
            for sid, count in unresolved.most_common()
            if sid in real_effect_sids
        },
        "artifacts": real_artifacts,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Artifact effect analysis")
    print(
        f"Artifacts: {len(real_artifacts)} | unique effects: {len(real_effect_sids)} | "
        f"effect prototypes loaded: {len(effects)} | unresolved: {report['summary']['unresolved_effect_sids']}"
    )
    print("\nEffect types:")
    if real_effect_types:
        for effect_type, count in real_effect_types.most_common():
            print(f"  {effect_type}: {count}")
    else:
        print("  (no EffectPrototype definitions resolved yet)")

    if report["unresolved_effects"]:
        print("\nUnresolved effect SIDs:")
        for sid, row in report["unresolved_effects"].items():
            print(f"  {sid}: {row['uses']} use(s)")

    print(f"\nReport: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
