from __future__ import annotations

import re
from pathlib import Path


CONTENT_ROOT = Path(__file__).resolve().parents[3]
PYTHON_ROOT = CONTENT_ROOT / "Python"
VANILLA_DYNAMIC_ITEM_GENERATOR = PYTHON_ROOT / "VanillaReference/DynamicItemGenerator.cfg"
OUTPUT_PATH = (
    CONTENT_ROOT
    / "GameLite/GameData/ItemGeneratorPrototypes/DynamicItemGenerator/DynamicItemGenerator_patch_BPRUE.cfg"
)

T1_KITS = (
    "BPRUE_Viper_PistolConversionKit",
    "BPRUE_AKU_PistolConversionKit",
)
T2_KITS = (
    "BPRUE_Bucket_PistolConversionKit",
    "BPRUE_Fora230_PistolConversionKit",
)
T3_KITS = (
    "BPRUE_Integral_PistolConversionKit",
    "BPRUE_Zubr_PistolConversionKit",
)

# Vanilla has no shared T1 attachment pool. These trader roots have a direct
# Attach category and expose T1 weapons either directly or through the T1 gun pool.
T1_DIRECT_ATTACH_TRADERS = (
    "TraderZalesie_TradeItemGenerator",
    "TraderChemicalPlant_TradeItemGenerator",
    "SultanskTrader_TradeItemGenerator",
    "EgerTrader_TradeItemGenerator",
)

CATEGORY_RE = re.compile(r"^\s*Category\s*=\s*EItemGenerationCategory::([^\s]+)\s*$")
STRUCT_BEGIN_RE = re.compile(r"^\s*([^:]+?)\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*$")


def _strip_comment(line: str) -> str:
    return line.split("//", 1)[0].rstrip()


def _top_level_generator_block(text: str, generator_sid: str) -> list[str]:
    """Return one top-level generator block from the Vanilla DynamicItemGenerator."""
    lines = text.splitlines()
    start = None
    depth = 0

    for index, raw_line in enumerate(lines):
        line = _strip_comment(raw_line)
        begin = STRUCT_BEGIN_RE.match(line)
        if start is None:
            if begin and begin.group(1).strip() == generator_sid:
                start = index
                depth = 1
            continue

        if begin:
            depth += 1
        elif line.strip() == "struct.end":
            depth -= 1
            if depth == 0:
                return lines[start:index + 1]

    raise ValueError(f"Vanilla generator not found or unterminated: {generator_sid}")


def _direct_item_generator_categories(block: list[str]) -> list[tuple[int, str]]:
    """Return effective array index + category for direct ItemGenerator children.

    Vanilla commonly writes these children as [*]. At load time each [*] appends
    the next array element, so the effective index is the child ordinal. We resolve
    that ordinal here and patch the concrete element instead of trying to bpatch [*].
    """
    item_generator_depth = None
    depth = 0
    child_depth = None
    child_index = -1
    current_index = None
    categories: list[tuple[int, str]] = []

    for raw_line in block:
        line = _strip_comment(raw_line)
        begin = STRUCT_BEGIN_RE.match(line)

        if begin:
            key = begin.group(1).strip()
            depth += 1
            if key == "ItemGenerator" and depth == 2:
                item_generator_depth = depth
                continue
            if item_generator_depth is not None and depth == item_generator_depth + 1:
                child_index += 1
                current_index = child_index
                child_depth = depth
            continue

        category = CATEGORY_RE.match(line)
        if (
            category
            and item_generator_depth is not None
            and child_depth is not None
            and depth == child_depth
            and current_index is not None
        ):
            categories.append((current_index, category.group(1)))
            continue

        if line.strip() == "struct.end":
            if child_depth is not None and depth == child_depth:
                child_depth = None
                current_index = None
            if item_generator_depth is not None and depth == item_generator_depth:
                item_generator_depth = None
            depth -= 1

    return categories


def _attachment_category_index(vanilla_text: str, generator_sid: str) -> int:
    block = _top_level_generator_block(vanilla_text, generator_sid)
    categories = _direct_item_generator_categories(block)
    matches = [index for index, category in categories if category == "Attach"]
    if len(matches) != 1:
        rendered = ", ".join(f"[{index}]={category}" for index, category in categories)
        raise ValueError(
            f"{generator_sid}: expected exactly one direct Attach category, "
            f"found {len(matches)}. Direct categories: {rendered or '(none)'}"
        )
    return matches[0]


def _item_block(item_sid: str, indent: str) -> list[str]:
    """Render a named PossibleItems child, matching known working trader patches."""
    return [
        f"{indent}{item_sid} : struct.begin",
        f"{indent}   ItemPrototypeSID = {item_sid}",
        f"{indent}   Chance = 1",
        f"{indent}   MinCount = 1",
        f"{indent}   MaxCount = 1",
        f"{indent}struct.end",
    ]


def _render_attachment_category_patch(
    generator_sid: str,
    category_index: int,
    kits: tuple[str, ...],
) -> list[str]:
    lines = [
        f"{generator_sid} : struct.begin {{bpatch}}",
        "   ItemGenerator : struct.begin {bpatch}",
        f"      [{category_index}] : struct.begin {{bpatch}}",
        "         PossibleItems : struct.begin {bpatch}",
    ]
    for kit_sid in kits:
        lines.extend(_item_block(kit_sid, "            "))
    lines += [
        "         struct.end",
        "      struct.end",
        "   struct.end",
        "struct.end",
        "",
    ]
    return lines


def render_trader_conversion_kit_patch() -> str:
    """Render BPRUE trader distribution using verified Vanilla category indices."""
    vanilla_text = VANILLA_DYNAMIC_ITEM_GENERATOR.read_text(encoding="utf-8-sig")

    targets = [
        *((sid, T1_KITS) for sid in T1_DIRECT_ATTACH_TRADERS),
        ("Trader_Attachments_T2_ItemGenerator", T1_KITS + T2_KITS),
        ("Trader_Attachments_T3_ItemGenerator", T3_KITS),
    ]
    resolved = [
        (sid, _attachment_category_index(vanilla_text, sid), kits)
        for sid, kits in targets
    ]

    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Source: Python/CFGGenerators/SMGs/trader_conversion_kits.py",
        "// BPRUE pistol-slot conversion kit trader distribution.",
        "// Attachment category indices are resolved from Vanilla DynamicItemGenerator.cfg",
        "// so bpatch targets an existing category instead of appending an ambiguous [*].",
        "// PossibleItems are added as named children, matching working trader patch syntax.",
        "// Progression: kit availability starts with the base weapon's trader tier.",
        "// Vanilla has no Trader_Attachments_T1_ItemGenerator; early direct Attach",
        "// categories are patched explicitly and T1 kits carry forward into T2.",
        "// -----------------------------------------------------------------------------",
        "",
    ]

    for generator_sid, category_index, kits in resolved:
        lines.append(f"// Vanilla Attach category: ItemGenerator[{category_index}]")
        lines.extend(_render_attachment_category_patch(generator_sid, category_index, kits))

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    content = render_trader_conversion_kit_patch()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
