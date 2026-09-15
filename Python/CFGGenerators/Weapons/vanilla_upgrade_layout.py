from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
VANILLA_UPGRADES = PYTHON_ROOT / "VanillaReference" / "UpgradePrototypes.cfg"


def _top_level_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] | None = None
    depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        if current is None:
            if not line.startswith((" ", "\t")) and ": struct.begin" in stripped:
                current = [line]
                depth = 1
            continue
        current.append(line)
        if "struct.begin" in stripped:
            depth += 1
        if stripped == "struct.end":
            depth -= 1
            if depth == 0:
                blocks.append(current)
                current = None
    return blocks


def _direct_scalar(block: list[str], name: str) -> str | None:
    prefix = name + " ="
    depth = 0
    for line in block[1:-1]:
        stripped = line.strip()
        if depth == 0 and stripped.startswith(prefix):
            return stripped.split("=", 1)[1].strip()
        if "struct.begin" in stripped:
            depth += 1
        if stripped == "struct.end":
            depth -= 1
    return None


@lru_cache(maxsize=1)
def vanilla_modification_max_columns() -> dict[str, int]:
    """Return max vanilla HorizontalPosition per UpgradeTargetPart.

    Only vanilla prototypes explicitly marked IsModification = true are relevant
    for the technician modification layout. Missing HorizontalPosition is treated
    as column 0, matching the game's default behaviour.
    """
    if not VANILLA_UPGRADES.exists():
        raise FileNotFoundError(
            f"Missing vanilla reference: {VANILLA_UPGRADES}. "
            "Keep UpgradePrototypes.cfg under Python/VanillaReference."
        )

    maxima: dict[str, int] = {}
    for block in _top_level_blocks(VANILLA_UPGRADES.read_text(encoding="utf-8")):
        if (_direct_scalar(block, "IsModification") or "").lower() != "true":
            continue
        target = _direct_scalar(block, "UpgradeTargetPart")
        if not target:
            continue
        target_name = target.rsplit("::", 1)[-1]
        raw_horizontal = _direct_scalar(block, "HorizontalPosition")
        horizontal = int(raw_horizontal) if raw_horizontal and re.fullmatch(r"-?\d+", raw_horizontal) else 0
        maxima[target_name] = max(maxima.get(target_name, -1), horizontal)
    return maxima


def first_bprue_column(target_part: str) -> int:
    """First column guaranteed to be to the right of vanilla modifications."""
    return vanilla_modification_max_columns().get(target_part, -1) + 1


def group_columns(target_part: str, groups: list[str]) -> dict[str, int]:
    start = first_bprue_column(target_part)
    return {group: start + index for index, group in enumerate(groups)}
