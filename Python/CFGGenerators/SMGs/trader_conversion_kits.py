from __future__ import annotations

from pathlib import Path


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

# These Vanilla trader roots have a direct Attach category and expose T1 weapons
# either directly or through Trader_T1_Guns_ItemGenerator. Traders without an
# attachment category (for example bartenders) are deliberately left untouched.
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


def _render_shared_attachment_pool(generator_sid: str, kits: tuple[str, ...]) -> list[str]:
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


def _render_direct_trader_attach_pool(generator_sid: str, kits: tuple[str, ...]) -> list[str]:
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
    """Render the first BPRUE trader-distribution draft for pistol conversion kits.

    Progression rule: a conversion kit becomes available from the same weapon tier
    as its base weapon. Vanilla has no shared T1 attachment generator, so T1 kits
    are added to direct early-trader Attach categories and to the shared T2 pool
    for forward availability. T2 kits enter T2; T3 kits enter T3.
    """
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// BPRUE pistol-slot conversion kit trader distribution.",
        "// Progression: kit availability starts with the base weapon's trader tier.",
        "// Vanilla has no Trader_Attachments_T1_ItemGenerator; early direct Attach",
        "// categories are patched explicitly and T1 kits carry forward into T2.",
        "// -----------------------------------------------------------------------------",
        "",
    ]

    for trader_sid in T1_DIRECT_ATTACH_TRADERS:
        lines.extend(_render_direct_trader_attach_pool(trader_sid, T1_KITS))

    # T2 carries T1 kits forward and introduces the T2 conversion kits.
    lines.extend(
        _render_shared_attachment_pool(
            "Trader_Attachments_T2_ItemGenerator",
            T1_KITS + T2_KITS,
        )
    )

    # Vanilla late traders reference T2 and T3 cumulatively, so T3 only needs the
    # newly unlocked T3 kits rather than duplicating lower-tier entries.
    lines.extend(
        _render_shared_attachment_pool(
            "Trader_Attachments_T3_ItemGenerator",
            T3_KITS,
        )
    )

    return "\n".join(lines).rstrip() + "\n"
