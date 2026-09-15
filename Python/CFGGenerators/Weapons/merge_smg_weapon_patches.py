from __future__ import annotations

from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
GENERAL_SETUP_DIR = CONTENT_ROOT / "GameLite" / "GameData" / "WeaponData" / "WeaponGeneralSetupPrototypes"
MODULES_PATH = GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE_SMGModules.cfg"
CONVERSIONS_PATH = GENERAL_SETUP_DIR / "WeaponGeneralSetupPrototypes_patch_BPRUE_SMGConversions.cfg"

# Keep the complete BPRUE GeneralSetup changes for these SMGs in one patch per
# weapon. This avoids separate files patching UpgradePrototypeSIDs and
# CompatibleAttachments on the same base prototype.
CONVERSION_ATTACHMENTS = {
    "GunViper_PP": (
        "BPRUE_Viper_PistolConversionKit",
        "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Viper/T_inv_w_viper_toprail.T_inv_w_viper_toprail'",
        "FrontRailSocket", 150, 30, "GunViper_Upgrade_BPRUE_PistolConversion",
    ),
    "GunAKU_PP": (
        "BPRUE_AKU_PistolConversionKit",
        "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/AKU/T_inv_w_aku_colimscope.T_inv_w_aku_colimscope'",
        "ColimScopeSocket", 155, 9, "GunAKU_Upgrade_BPRUE_PistolConversion",
    ),
    "GunBucket_PP": (
        "BPRUE_Bucket_PistolConversionKit",
        "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Bucket/T_inv_w_bucket_en_colimscope_1.T_inv_w_bucket_en_colimscope_1'",
        "ColimScopeSocket", 155, 9, "GunBucket_Upgrade_BPRUE_PistolConversion",
    ),
    "GunIntegral_PP": (
        "BPRUE_Integral_PistolConversionKit",
        "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Integral/T_inv_w_integral_en_goloscope_1.T_inv_w_integral_en_goloscope_1'",
        "GoloScopeSocket", 155, 9, "GunIntegral_Upgrade_BPRUE_PistolConversion",
    ),
    "GunZubr_PP": (
        "BPRUE_Zubr_PistolConversionKit",
        "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Zubr/T_inv_w_zubr_ru_colimscope_mini_1.T_inv_w_zubr_ru_colimscope_mini_1'",
        "ColimScopeSocket", 155, 9, "GunZubr_Upgrade_BPRUE_PistolConversion",
    ),
    "GunFora230_PP_GS": (
        "BPRUE_Fora230_PistolConversionKit",
        "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/Inventory/WeaponAndAttachments/Viper/T_inv_w_viper_toprail.T_inv_w_viper_toprail'",
        "ColimScopeSocket", 155, 9, "GunFora230_Upgrade_BPRUE_PistolConversion",
    ),
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


def merge_modules() -> None:
    text = MODULES_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    out: list[str] = []
    current_sid: str | None = None
    depth = 0

    for line in lines:
        stripped = line.strip()
        if depth == 0 and stripped.endswith(": struct.begin {bpatch}"):
            current_sid = stripped.split(" :", 1)[0]

        if "struct.begin" in stripped:
            depth += 1

        if stripped == "struct.end":
            if depth == 1 and current_sid in CONVERSION_ATTACHMENTS:
                out.extend(attachment_block(CONVERSION_ATTACHMENTS[current_sid]))
            depth -= 1
            if depth == 0:
                current_sid = None

        out.append(line)

    MODULES_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    merge_modules()
    if CONVERSIONS_PATH.exists():
        CONVERSIONS_PATH.unlink()
    print(f"Consolidated all SMG weapon patches in {MODULES_PATH}")


if __name__ == "__main__":
    main()
