from __future__ import annotations

from pathlib import Path


CONTENT_ROOT = Path(__file__).resolve().parents[3]
OUTPUT_PATH = (
    CONTENT_ROOT
    / "GameLite/GameData/ItemGeneratorPrototypes/DynamicItemGenerator_patch_BPRUE.cfg"
)

# Vanilla has shared T2/T3/T4 attachment generators, but no
# Trader_Attachments_T1_ItemGenerator. T1 therefore needs two pieces:
#   1. patch the direct Attach category of early/T1 traders that actually have one;
#   2. also add the T1 kits to T2 so they remain available once progression moves on.
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
# Bartenders that sell weapons but no attachments are deliberately left untouched.
T1_DIRECT_ATTACH_TRADERS = (
    "TraderZalesie_TradeItemGenerator",
    "TraderChemicalPlant_TradeItemGenerator",
    "SultanskTrader_TradeItemGenerator",
    "EgerTrader_TradeItemGenerator",
)


def _item_block(item_sid: str, indent: str) -> list[str]:
    return [
        f"{indent}[*] : struct.begin",
        f"{indent}   ItemPrototypeSID = {item_sid}",
        f"{indent}   Chance = 1",
        f"{indent}   MinCount = 1",
        f"{indent}   MaxCount = 1",
        f"{indent}struct.end",
    ]


def _render_attachment_category_patch(generator_sid: str, kits: tuple[str, ...]) -> list[str]:
    lines = [
        f"{generator_sid} : struct.begin {{bpatch}}",
        "   ItemGenerator : struct.begin {bpatch}",
        "      [*] : struct.begin {bpatch}",
        "         Category = EItemGenerationCategory::Attach",
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
    """Render the first BPRUE trader-distribution draft for conversion kits.

    Progression rule: a conversion kit becomes available with its base weapon tier.
    T1 has no shared Vanilla attachment generator, so early direct Attach categories
    are patched and the T1 kits are carried forward in the shared T2 pool.
    """
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Source: Python/CFGGenerators/SMGs/trader_conversion_kits.py",
        "// BPRUE pistol-slot conversion kit trader distribution.",
        "// Progression: kit availability starts with the base weapon's trader tier.",
        "// Vanilla has no Trader_Attachments_T1_ItemGenerator; early direct Attach",
        "// categories are patched explicitly and T1 kits carry forward into T2.",
        "// -----------------------------------------------------------------------------",
        "",
    ]

    for trader_sid in T1_DIRECT_ATTACH_TRADERS:
        lines.extend(_render_attachment_category_patch(trader_sid, T1_KITS))

    # T2 carries T1 forward and introduces Bucket/Fora.
    lines.extend(
        _render_attachment_category_patch(
            "Trader_Attachments_T2_ItemGenerator",
            T1_KITS + T2_KITS,
        )
    )

    # Late Vanilla traders reference lower attachment tiers cumulatively, so T3
    # only introduces Integral/Zubr rather than duplicating all lower-tier kits.
    lines.extend(
        _render_attachment_category_patch(
            "Trader_Attachments_T3_ItemGenerator",
            T3_KITS,
        )
    )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(render_trader_conversion_kit_patch(), encoding="utf-8")
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
