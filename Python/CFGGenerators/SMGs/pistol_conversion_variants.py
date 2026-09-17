from __future__ import annotations

"""Pistol-slot conversion variant metadata.

Converted SMG items intentionally keep their inherited BaseGame
GeneralWeaponSetup. Creating a new GeneralSetup SID for the converted item can
break runtime weapon/animation lookups even when that setup inherits all
BaseGame properties.

The conversion upgrade itself must therefore be prevented from being offered a
second time by requirement/upgrade logic, not by cloning the GeneralSetup and
removing the upgrade from UpgradePrototypeSIDs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PistolConversionVariant:
    weapon_sid: str
    source_weapon_sid: str
    conversion_upgrade_sid: str


PISTOL_CONVERSION_VARIANTS: tuple[PistolConversionVariant, ...] = (
    PistolConversionVariant("BPRUE_GunViper_Pistol_PP", "GunViper_PP", "GunViper_Upgrade_BPRUE_PistolConversion"),
    PistolConversionVariant("BPRUE_GunAKU_Pistol_PP", "GunAKU_PP", "GunAKU_Upgrade_BPRUE_PistolConversion"),
    PistolConversionVariant("BPRUE_GunBucket_Pistol_PP", "GunBucket_PP", "GunBucket_Upgrade_BPRUE_PistolConversion"),
    PistolConversionVariant("BPRUE_GunIntegral_Pistol_PP", "GunIntegral_PP", "GunIntegral_Upgrade_BPRUE_PistolConversion"),
    PistolConversionVariant("BPRUE_GunZubr_Pistol_PP", "GunZubr_PP", "GunZubr_Upgrade_BPRUE_PistolConversion"),
    PistolConversionVariant("BPRUE_GunFora230_Pistol_PP", "GunFora230_PP", "GunFora230_Upgrade_BPRUE_PistolConversion"),
)
