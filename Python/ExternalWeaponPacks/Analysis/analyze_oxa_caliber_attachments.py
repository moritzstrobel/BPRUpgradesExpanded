from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = ROOT / "Python"
sys.path.insert(0, str(PYTHON_ROOT / "Analysis"))

from analyze_oxa_conflicts import collect, collect_vanilla, _semantic_arrays, _writes_by_semantic_group, _apply_array_patch, _entry_identity  # noqa: E402

VANILLA_ROOT = PYTHON_ROOT / "VanillaReference"
OXA_ROOT = VANILLA_ROOT / "OxaData"
OUT_TXT = ROOT / "Python/ExternalWeaponPacks/Reports/oxa_caliber_attachments.txt"
OUT_JSON = ROOT / "Python/ExternalWeaponPacks/Reports/oxa_caliber_attachments.json"

CALIBERS = {
    "A545": ("545", "5.45", "545x39"),
    "A556": ("556", "5.56", "556x45"),
    "A762": ("762x39", "7.62x39"),
    "A762NATO": ("762x51", "7.62x51", "308"),
}
TYPE_HINTS = {
    "magazine": ("mag", "pmag", "emag"),
    "muzzle": ("muzzle", "muz", "vent", "comp", "brake"),
    "silencer": ("silen", "silencer", "suppress"),
}


def effective_fitting(vanilla, oxa):
    vg, og = _semantic_arrays(vanilla), _writes_by_semantic_group(oxa)
    keys = {key for key in set(vg) | set(og) if key[1] == "FittingWeaponsSIDs"}
    result = {}
    for prototype, root in keys:
        key = (prototype, root)
        base = {i: dict(f) for i, f in vg.get(key, {"entries": {}})["entries"].items()}
        state, _ = _apply_array_patch(base, og.get(key, []), root)
        result[prototype] = sorted(
            identity for fields in state.values()
            if (identity := _entry_identity(root, fields)) is not None
        )
    return result


def detect_caliber(sid: str) -> str | None:
    lower = sid.lower()
    hits = []
    for caliber, tokens in CALIBERS.items():
        if any(token.lower() in lower for token in tokens):
            hits.append(caliber)
    return hits[0] if len(hits) == 1 else None


def detect_type(sid: str) -> str:
    lower = sid.lower()
    for kind, hints in TYPE_HINTS.items():
        if any(hint in lower for hint in hints):
            return kind
    return "other"


def main() -> None:
    vanilla, oxa = collect_vanilla(VANILLA_ROOT), collect(OXA_ROOT)
    fitting = effective_fitting(vanilla, oxa)

    rows = defaultdict(list)
    for sid, weapons in sorted(fitting.items()):
        caliber = detect_caliber(sid)
        if caliber:
            rows[caliber].append({
                "sid": sid,
                "type": detect_type(sid),
                "fitting_weapons": weapons,
            })

    lines = ["OXA caliber-specific attachment inventory", "=========================================", ""]
    for caliber in CALIBERS:
        items = rows[caliber]
        lines += [caliber, "=" * len(caliber), f"Attachments: {len(items)}"]
        by_type = defaultdict(list)
        for item in items:
            by_type[item["type"]].append(item)
        for kind in ("magazine", "muzzle", "silencer", "other"):
            if not by_type[kind]:
                continue
            lines.append(f"  {kind}:")
            for item in by_type[kind]:
                owners = ", ".join(item["fitting_weapons"]) or "-"
                lines.append(f"    {item['sid']} -> {owners}")
        lines.append("")

    OUT_TXT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TXT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"calibers": dict(rows)}, indent=2), encoding="utf-8")
    print(OUT_TXT.read_text(encoding="utf-8"), end="")
    print(f"Text report: {OUT_TXT.relative_to(ROOT).as_posix()}")
    print(f"JSON report: {OUT_JSON.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
