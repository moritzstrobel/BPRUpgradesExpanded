from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "Python/ExternalWeaponPacks/weapon_packs.json"
OXA_ROOT = ROOT / "Python/VanillaReference/OxaData"
VANILLA_ROOT = ROOT / "Python/VanillaReference"
OUT_TXT = ROOT / "Python/ExternalWeaponPacks/Reports/oxa_parent_deltas.txt"
OUT_JSON = ROOT / "Python/ExternalWeaponPacks/Reports/oxa_parent_deltas.json"

sys.path.insert(0, str(ROOT / "Python/Analysis"))
from analyze_oxa_conflicts import (  # noqa: E402
    collect, collect_vanilla, _semantic_arrays, _writes_by_semantic_group,
    _apply_array_patch, _entry_identity,
)

TOP = re.compile(r"(?m)^([A-Za-z0-9_]+)\s*:\s*struct\.begin(?:\s*\{([^}]*)\})?")
ATTACH_BLOCK = re.compile(r"(?ms)^\s*\[\d+\]\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*(.*?)^\s*struct\.end")
ATTACH_SID = re.compile(r"(?m)^\s*AttachPrototypeSID\s*=\s*([^\s/]+)")
FIT_ARRAY = re.compile(r"(?ms)^\s*FittingWeaponsSIDs\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*(.*?)^\s*struct\.end")
INDEXED = re.compile(r"(?m)^\s*\[\d+\]\s*=\s*([^\s/]+)")
SCALAR = re.compile(r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*(.+?)\s*$")


def blocks(text: str):
    text = text.lstrip("\ufeff")
    matches = list(TOP.finditer(text))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        yield match.group(1), text[match.start():end]


def cfg_files(root: Path):
    return sorted(root.rglob("*.cfg")) if root.exists() else []


def normalized_entry(body: str) -> dict:
    fields = {}
    for key, value in SCALAR.findall(body):
        value = value.split("//", 1)[0].strip()
        if value:
            fields[key] = value
    # Preserve nested requirement/list values as normalized SID lists.
    for name in ("RequiredUpgradeIDs", "RequiredAttachPrototypeSIDs"):
        match = re.search(
            rf"(?ms)^\s*{name}\s*:\s*struct\.begin(?:\s*\{{[^}}]*\}})?\s*(.*?)^\s*struct\.end",
            body,
        )
        if match:
            fields[name] = sorted(INDEXED.findall(match.group(1)))
    return fields


def effective_array_entries(vanilla_writes, oxa_writes, prototype: str, root: str) -> tuple[dict[str, dict], dict[str, dict]]:
    """Return Vanilla and effective OXA entries keyed by semantic identity."""
    key = (prototype, root)
    vanilla_groups = _semantic_arrays(vanilla_writes)
    oxa_groups = _writes_by_semantic_group(oxa_writes)
    base = {
        idx: dict(fields)
        for idx, fields in vanilla_groups.get(key, {"entries": {}})["entries"].items()
    }
    effective, _ = _apply_array_patch(base, oxa_groups.get(key, []), root)

    def by_identity(state: dict[str, dict]) -> dict[str, dict]:
        result = {}
        for fields in state.values():
            identity = _entry_identity(root, fields)
            if identity is not None:
                result[identity] = dict(fields)
        return result

    return by_identity(base), by_identity(effective)


def fitting_memberships(entries: dict[str, dict], weapon_sid: str) -> dict[str, list[str]]:
    """Invert effective FittingWeaponsSIDs arrays to attachments fitting source weapon."""
    return {
        attachment_sid: sorted(fields.get("_members", []))
        for attachment_sid, fields in entries.items()
        if weapon_sid in fields.get("_members", [])
    }


def effective_fitting_entries(vanilla_writes, oxa_writes) -> tuple[dict[str, dict], dict[str, dict]]:
    """Build effective FittingWeaponsSIDs membership per attachment prototype."""
    vanilla_groups = _semantic_arrays(vanilla_writes)
    oxa_groups = _writes_by_semantic_group(oxa_writes)
    keys = {key for key in set(vanilla_groups) | set(oxa_groups) if key[1] == "FittingWeaponsSIDs"}
    vanilla_result, oxa_result = {}, {}
    for prototype, root in keys:
        key = (prototype, root)
        base = {idx: dict(fields) for idx, fields in vanilla_groups.get(key, {"entries": {}})["entries"].items()}
        effective, _ = _apply_array_patch(base, oxa_groups.get(key, []), root)
        vanilla_result[prototype] = {"_members": [v for f in base.values() if (v := _entry_identity(root, f)) is not None]}
        oxa_result[prototype] = {"_members": [v for f in effective.values() if (v := _entry_identity(root, f)) is not None]}
    return vanilla_result, oxa_result

