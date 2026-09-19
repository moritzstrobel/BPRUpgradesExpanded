from __future__ import annotations

from pathlib import Path

from CFGGenerators.Common.vanilla_upgrade_layout import (
    _direct_child,
    _general_setup_blocks,
    _indexed_children,
)

CONVERSION_ATTACHMENTS = {
    "GunViper_PP": ("BPRUE_Viper_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Viper/T_inv_w_viper_toprail.T_inv_w_viper_toprail'", "FrontRailSocket", 150, 30, "GunViper_Upgrade_BPRUE_PistolConversion"),
    "GunAKU_PP": ("BPRUE_AKU_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/AKU/T_inv_w_aku_colimscope.T_inv_w_aku_colimscope'", "ColimScopeSocket", 155, 9, "GunAKU_Upgrade_BPRUE_PistolConversion"),
    "GunBucket_PP": ("BPRUE_Bucket_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Bucket/T_inv_w_bucket_en_colimscope_1.T_inv_w_bucket_en_colimscope_1'", "ColimScopeSocket", 155, 9, "GunBucket_Upgrade_BPRUE_PistolConversion"),
    "GunIntegral_PP": ("BPRUE_Integral_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Integral/T_inv_w_integral_en_goloscope_1.T_inv_w_integral_en_goloscope_1'", "GoloScopeSocket", 155, 9, "GunIntegral_Upgrade_BPRUE_PistolConversion"),
    "GunZubr_PP": ("BPRUE_Zubr_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Zubr/T_inv_w_zubr_ru_colimscope_mini_1.T_inv_w_zubr_ru_colimscope_mini_1'", "ColimScopeSocket", 155, 9, "GunZubr_Upgrade_BPRUE_PistolConversion"),
    "GunFora230_PP_GS": ("BPRUE_Fora230_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Viper/T_inv_w_viper_toprail.T_inv_w_viper_toprail'", "ColimScopeSocket", 155, 9, "GunFora230_Upgrade_BPRUE_PistolConversion"),
}


def _reindex_struct(block: list[str], index: int) -> list[str]:
    rendered = list(block)
    indent = rendered[0][: len(rendered[0]) - len(rendered[0].lstrip())]
    rendered[0] = f"{indent}[{index}] : struct.begin"
    return rendered


def _vanilla_compatible_attachments(setup_sid: str) -> list[list[str]]:
    block = _general_setup_blocks().get(setup_sid)
    if not block:
        raise ValueError(f"No Vanilla GeneralSetup found for conversion weapon {setup_sid}")

    compatible = _direct_child(block, "CompatibleAttachments")
    if compatible is None:
        raise ValueError(f"No Vanilla CompatibleAttachments found for conversion weapon {setup_sid}")

    entries = _indexed_children(compatible)
    if not entries:
        raise ValueError(f"Vanilla CompatibleAttachments is empty for conversion weapon {setup_sid}")
    return entries


def attachment_block(setup_sid: str, data: tuple[str, str, str, int, int, str]) -> list[str]:
    """Render a complete deterministic CompatibleAttachments array.

    Appending the conversion kit with [*] can disturb inherited Vanilla attachment
    entries for some SMGs (confirmed with RU_Silen_1 on Zubr/Bucket). Re-render the
    directly owned Vanilla array and put the conversion kit at the next numeric
    index instead.
    """
    attach_sid, icon, socket, x, y, upgrade_sid = data
    vanilla_entries = _vanilla_compatible_attachments(setup_sid)

    lines = ["   CompatibleAttachments : struct.begin"]
    for index, entry in enumerate(vanilla_entries):
        lines.extend(_reindex_struct(entry, index))

    index = len(vanilla_entries)
    lines += [
        f"      [{index}] : struct.begin",
        f"         AttachPrototypeSID = {attach_sid}",
        f"         WeaponSpecificIcon = {icon}",
        f"         Socket = {socket}",
        f"         IconPosX = {x}",
        f"         IconPosY = {y}",
        "         RequiredUpgradeIDs : struct.begin",
        f"            [0] = {upgrade_sid}",
        "         struct.end",
        "      struct.end",
        "   struct.end",
    ]
    return lines
