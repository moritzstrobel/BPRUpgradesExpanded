from __future__ import annotations

CONVERSION_ATTACHMENTS = {
    "GunViper_PP": ("BPRUE_Viper_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Viper/T_inv_w_viper_toprail.T_inv_w_viper_toprail'", "FrontRailSocket", 150, 30, "GunViper_Upgrade_BPRUE_PistolConversion"),
    "GunAKU_PP": ("BPRUE_AKU_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/AKU/T_inv_w_aku_colimscope.T_inv_w_aku_colimscope'", "ColimScopeSocket", 155, 9, "GunAKU_Upgrade_BPRUE_PistolConversion"),
    "GunBucket_PP": ("BPRUE_Bucket_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Bucket/T_inv_w_bucket_en_colimscope_1.T_inv_w_bucket_en_colimscope_1'", "ColimScopeSocket", 155, 9, "GunBucket_Upgrade_BPRUE_PistolConversion"),
    "GunIntegral_PP": ("BPRUE_Integral_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Integral/T_inv_w_integral_en_goloscope_1.T_inv_w_integral_en_goloscope_1'", "GoloScopeSocket", 155, 9, "GunIntegral_Upgrade_BPRUE_PistolConversion"),
    "GunZubr_PP": ("BPRUE_Zubr_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Zubr/T_inv_w_zubr_ru_colimscope_mini_1.T_inv_w_zubr_ru_colimscope_mini_1'", "ColimScopeSocket", 155, 9, "GunZubr_Upgrade_BPRUE_PistolConversion"),
    "GunFora230_PP_GS": ("BPRUE_Fora230_PistolConversionKit", "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Viper/T_inv_w_viper_toprail.T_inv_w_viper_toprail'", "ColimScopeSocket", 155, 9, "GunFora230_Upgrade_BPRUE_PistolConversion"),
}


def attachment_block(data: tuple[str, str, str, int, int, str]) -> list[str]:
    attach_sid, icon, socket, x, y, upgrade_sid = data
    return [
        "   CompatibleAttachments : struct.begin {bpatch}",
        "      [*] : struct.begin",
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
