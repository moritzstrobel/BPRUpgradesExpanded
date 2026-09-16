from __future__ import annotations

from dataclasses import dataclass

from upgrade_build_model import UpgradeBuildModel
from vanilla_upgrade_layout import vanilla_general_setup_upgrades


@dataclass(frozen=True)
class PistolConversionVariant:
    """One runtime weapon replacement produced by a pistol-slot conversion quest.

    The quest replaces the original weapon item with ``weapon_sid``.  That
    replacement must use its own GeneralSetup so the conversion upgrade can be
    removed without changing the upgrade tree of the original weapon.
    """

    weapon_sid: str
    source_general_setup_sid: str
    variant_general_setup_sid: str
    conversion_upgrade_sid: str


# Runtime replacement weapon SIDs live in the conversion quest assets rather
# than GameData. Fill these entries with the exact replacement SIDs from those
# assets before enabling generation.  Keeping the mapping empty is deliberate:
# guessing a runtime SID would generate a valid-looking but broken GameData
# patch.
PISTOL_CONVERSION_VARIANTS: tuple[PistolConversionVariant, ...] = ()


def _final_upgrade_sids(
    model: UpgradeBuildModel,
    setup_sid: str,
    vanilla: dict[str, list[str]],
) -> list[str]:
    """Return the exact final Vanilla + BPRUE array used by the main renderer."""
    if setup_sid not in vanilla:
        raise ValueError(f"No effective UpgradePrototypeSIDs found for {setup_sid}")
    bprue = model.by_general_setup().get(setup_sid, [])
    return list(dict.fromkeys([*vanilla[setup_sid], *(upgrade.sid for upgrade in bprue)]))


def render_pistol_conversion_variant_patches(model: UpgradeBuildModel) -> tuple[str, str]:
    """Render GeneralSetup + WeaponPrototype patches for converted SMG items.

    The conversion upgrade index is resolved from the *final* combined upgrade
    array.  No numeric index is stored in configuration, so adding/removing
    BPRUE upgrades cannot silently make the removenode target stale.

    Returns ``(general_setup_text, weapon_patch_text)``.  With no configured
    runtime variants both strings are empty.
    """
    if not PISTOL_CONVERSION_VARIANTS:
        return "", ""

    vanilla = vanilla_general_setup_upgrades()
    setup_lines: list[str] = []
    weapon_lines: list[str] = []

    seen_weapons: set[str] = set()
    seen_variant_setups: set[str] = set()

    for variant in PISTOL_CONVERSION_VARIANTS:
        if variant.weapon_sid in seen_weapons:
            raise ValueError(f"Duplicate pistol conversion weapon SID: {variant.weapon_sid}")
        if variant.variant_general_setup_sid in seen_variant_setups:
            raise ValueError(
                f"Duplicate pistol conversion GeneralSetup SID: {variant.variant_general_setup_sid}"
            )
        seen_weapons.add(variant.weapon_sid)
        seen_variant_setups.add(variant.variant_general_setup_sid)

        final_sids = _final_upgrade_sids(model, variant.source_general_setup_sid, vanilla)
        matches = [
            index
            for index, sid in enumerate(final_sids)
            if sid == variant.conversion_upgrade_sid
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{variant.source_general_setup_sid}: expected exactly one "
                f"{variant.conversion_upgrade_sid} in final UpgradePrototypeSIDs, "
                f"found {len(matches)}"
            )
        conversion_index = matches[0]

        # Start from the exact final source array, then remove the conversion
        # node by its dynamically resolved index.  removenode is intentionally
        # emitted only after the complete array is known.
        setup_lines += [
            f"{variant.variant_general_setup_sid} : struct.begin "
            f"{{refkey={variant.source_general_setup_sid}}}",
            f"   SID = {variant.variant_general_setup_sid}",
            "   UpgradePrototypeSIDs : struct.begin {bpatch}",
            f"      [{conversion_index}] : removenode",
            "   struct.end",
            "struct.end",
            "",
        ]
        weapon_lines += [
            f"{variant.weapon_sid} : struct.begin {{bpatch}}",
            f"   GeneralWeaponSetup = {variant.variant_general_setup_sid}",
            "struct.end",
            "",
        ]

    return (
        "\n".join(setup_lines).rstrip() + "\n",
        "\n".join(weapon_lines).rstrip() + "\n",
    )
