from __future__ import annotations

from technician_support import (
    dlc_technician_general_setups,
    technician_upgrade_assignments,
    vanilla_technician_direct_upgrade_indices,
)
from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from vanilla_upgrade_layout import dlc_general_setup_upgrades, vanilla_general_setup_upgrades

ICON_ROOT = "/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons"
BPRUE_MODULE_IMAGE = "Texture2D'/BPRUpgradesExpanded/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/T_Module_Base.T_Module_Base'"
BPRUE_UNIQUE_MODULE_IMAGE = "Texture2D'/BPRUpgradesExpanded/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/T_Module_Base_Unique.T_Module_Base_Unique'"


def _vanilla_icon(name: str) -> str:
    asset = f"T_PDA_Upgrades_Icon_{name}"
    return f"Texture2D'{ICON_ROOT}/{asset}.{asset}'"

EFFECT_ICON_RULES = (
    (("ChangeCaliber", "ChangeAmmoTypes"), "CaliberChange"), (("ChangeFireType",), "Autosh"), (("ProjectileSpeed",), "Velocity"),
    (("DamageFalloff",), "DropDamage"), (("FireDistance",), "Range"), (("ArmorPen", "ArmorPiercing"), "ArmorPiercing"),
    (("DurabilityPerShot",), "ShootingDepreciation"), (("Durability",), "Depreciation"), (("WeaponWithdraw",), "Readiness"),
    (("AimingMovement",), "MovementAiming"), (("ShotRecovery",), "AimingReturn"), (("DispersionIncreaseSpeed",), "SlowingSpread"),
    (("MaxDispersion",), "MaxSpread"), (("IdleSway",), "AimingAccuracy"), (("AimingTime",), "AimingSpeed"),
    (("Dispersion",), "SpreadReduction"), (("Weight",), "WeightLoss"), (("Recoil",), "Recoil"),
)
GROUP_ICON_FALLBACKS = {
    "Caliber": "CaliberChange", "Conversion": "CaliberChange", "FireControl": "Autosh", "FireRate": "Velocity",
    "Reload": "Readiness", "Readiness": "Readiness", "Stock": "MovementAiming", "Handling": "MovementAiming",
    "Marksman": "AimingAccuracy", "Ballistics": "Range", "Pattern": "SpreadReduction", "Signature": "ShootingDepreciation", "Action": "Recoil",
}

# Caliber conversion descriptions must follow the actual effect profile, not only
# the target caliber. This matters especially for 9x19, whose trade-offs differ
# depending on the source weapon's original caliber.
CALIBER_HINT_EFFECT_MARKERS = (
    (("BPRUE_DamagePos15Effect", "BPRUE_ArmorPiercingPos15Effect", "BPRUE_RecoilPenalty25Effect"), "sid_bprue_caliber_762_eastern_tradeoff_description"),
    (("BPRUE_DamagePos10Effect", "BPRUE_ArmorPiercingPos15Effect", "BPRUE_RecoilPenalty20Effect", "BPRUE_DurabilityPerShotNeg15Effect"), "sid_bprue_caliber_762_nato_tradeoff_description"),
    (("BPRUE_SMG_DamagePos10Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_RecoilPenalty10Effect"), "sid_bprue_smg_caliber_918_to_919_description"),
    (("BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_DurabilityPerShotPos10Effect", "BPRUE_SMG_DamagePenalty10Effect"), "sid_bprue_smg_caliber_919_to_918_description"),
    (("BPRUE_SMG_DamagePos15Effect", "BPRUE_SMG_RecoilPenalty20Effect", "BPRUE_SMG_EffectiveRangePenalty10Effect"), "sid_bprue_smg_caliber_919_to_045_description"),
    (("BPRUE_SMG_RecoilPos10Effect", "BPRUE_SMG_EffectiveRangePos10Effect", "BPRUE_SMG_DamagePenalty10Effect"), "sid_bprue_smg_caliber_045_to_919_description"),
    (("BPRUE_SMG_DamagePos15Effect", "BPRUE_SMG_RecoilPenalty25Effect", "BPRUE_SMG_EffectiveRangePenalty15Effect"), "sid_bprue_smg_caliber_918_to_045_description"),
    (("BPRUE_SMG_RecoilPos15Effect", "BPRUE_SMG_EffectiveRangePos15Effect", "BPRUE_SMG_DamagePenalty15Effect"), "sid_bprue_smg_caliber_045_to_918_description"),
)


def semantic_upgrade_icon(upgrade: UpgradeDefinition) -> str:
    for needles, icon_name in EFFECT_ICON_RULES:
        if any(needle in effect for effect in upgrade.effects for needle in needles): return _vanilla_icon(icon_name)
    fallback = GROUP_ICON_FALLBACKS.get(upgrade.group)
    return _vanilla_icon(fallback) if fallback else upgrade.icon


def semantic_upgrade_hint(upgrade: UpgradeDefinition) -> str:
    if upgrade.group != "Caliber": return upgrade.hint_sid
    effect_set = set(upgrade.effects)
    for markers, hint_sid in CALIBER_HINT_EFFECT_MARKERS:
        if all(marker in effect_set for marker in markers): return hint_sid
    return upgrade.hint_sid


def upgrade_module_image(upgrade: UpgradeDefinition) -> str:
    return BPRUE_UNIQUE_MODULE_IMAGE if upgrade.group == "Signature" else BPRUE_MODULE_IMAGE


def _render_upgrade(upgrade: UpgradeDefinition, fallback_template: str | None = None) -> list[str]:
    template = upgrade.template_sid or fallback_template
    if not template: raise ValueError(f"{upgrade.sid}: no template SID configured")
    lines = [f"{upgrade.sid} : struct.begin {{refkey={template}}}", f"   SID = {upgrade.sid}", f"   Text = {upgrade.text_sid}", f"   Hint = {semantic_upgrade_hint(upgrade)}", f"   Image = {upgrade_module_image(upgrade)}", f"   Icon = {semantic_upgrade_icon(upgrade)}", f"   BaseCost = {upgrade.cost}"]
    if upgrade.horizontal_position is not None: lines.append(f"   HorizontalPosition = {upgrade.horizontal_position}")
    if upgrade.vertical_position is not None: lines.append(f"   VerticalPosition = EUpgradeVerticalPosition::{upgrade.vertical_position}")
    lines.append(f"   UpgradeTargetPart = EUpgradeTargetPartType::{upgrade.target_part}")
    if upgrade.effects:
        lines.append("   EffectPrototypeSIDs : struct.begin"); lines += [f"      [{i}] = {effect}" for i, effect in enumerate(upgrade.effects)]; lines.append("   struct.end")
    if upgrade.blocking_sids:
        lines.append("   BlockingUpgradePrototypeSIDs : struct.begin"); lines += [f"      [{i}] = {sid}" for i, sid in enumerate(upgrade.blocking_sids)]; lines.append("   struct.end")
    return lines + ["struct.end", ""]


def render_upgrade_prototypes(model: UpgradeBuildModel, *, source: str, template_sid: str, header_comments: tuple[str, ...] = ()) -> str:
    lines = [f"// AUTO-GENERATED - Source: {source} via UpgradeBuildModel", *(f"// {x}" for x in header_comments), "", f"{template_sid} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}", f"   SID = {template_sid}", "   IsModification = true", "struct.end", ""]
    for upgrade in model.upgrades: lines += _render_upgrade(upgrade, template_sid)
    return "\n".join(lines)


def render_consolidated_upgrade_prototypes(model: UpgradeBuildModel) -> str:
    lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// Final BPRUE weapon upgrade graph rendered directly from UpgradeBuildModel.", "// -----------------------------------------------------------------------------", ""]
    for template in dict.fromkeys(u.template_sid for u in model.upgrades if u.template_sid):
        lines += [f"{template} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}", f"   SID = {template}", "   IsModification = true", "struct.end", ""]
    for upgrade in model.upgrades: lines += _render_upgrade(upgrade)
    return "\n".join(lines).rstrip() + "\n"


def render_general_setup_patch(model: UpgradeBuildModel, *, header_comments: tuple[str, ...] = ()) -> str:
    lines = ["// AUTO-GENERATED - Source: UpgradeBuildModel", *(f"// {x}" for x in header_comments), ""]
    for setup_sid, upgrades in model.by_general_setup().items():
        lines += [f"{setup_sid} : struct.begin {{bpatch}}"]
        for name, value in model.general_setup_properties(setup_sid): lines.append(f"   {name} = {value}")
        lines += ["   UpgradePrototypeSIDs : struct.begin {bpatch}", *(f"      [*] = {u.sid}" for u in upgrades), "   struct.end", "struct.end", ""]
    return "\n".join(lines)


def _render_final_setup(model: UpgradeBuildModel, vanilla: dict[str, list[str]], *, scope: str, attachment_blocks: dict[str, list[str]] | None = None) -> str:
    attachments = attachment_blocks or {}; lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", f"// Scope: {scope}", "// UpgradePrototypeSIDs are one complete indexed Vanilla + BPRUE array.", "// -----------------------------------------------------------------------------", ""]
    for setup_sid, upgrades in model.by_general_setup().items():
        if setup_sid not in vanilla: raise ValueError(f"{scope}: no effective UpgradePrototypeSIDs found for {setup_sid}")
        combined = list(dict.fromkeys([*vanilla[setup_sid], *(u.sid for u in upgrades)]))
        lines.append(f"{setup_sid} : struct.begin {{bpatch}}")
        for name, value in model.general_setup_properties(setup_sid): lines.append(f"   {name} = {value}")
        lines += ["   UpgradePrototypeSIDs : struct.begin", *(f"      [{i}] = {sid}" for i, sid in enumerate(combined)), "   struct.end"]
        lines += attachments.get(setup_sid, []); lines += ["struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_final_general_setup_patch(model: UpgradeBuildModel, attachment_blocks: dict[str, list[str]] | None = None) -> str:
    return _render_final_setup(model, vanilla_general_setup_upgrades(), scope="BaseGame", attachment_blocks=attachment_blocks)


def render_dlc_general_setup_patch(model: UpgradeBuildModel, content_pack: str) -> str:
    return _render_final_setup(model, dlc_general_setup_upgrades(content_pack), scope=f"DLCGameData/{content_pack}")


def render_technician_patch(
    model: UpgradeBuildModel,
    *,
    dlc_models: dict[str, UpgradeBuildModel] | None = None,
) -> str:
    assignments = technician_upgrade_assignments(model)
    direct_owners = vanilla_technician_direct_upgrade_indices()

    # DLC upgrades live in separate models, but technician capability still lives
    # in BaseGame NPCPrototypes. Merge them into the same indexed NPC patch.
    for content_pack, dlc_model in sorted((dlc_models or {}).items()):
        support = dlc_technician_general_setups(content_pack)
        candidates = dlc_model.technician_upgrades()
        for technician_sid, supported_setups in support.items():
            if technician_sid not in direct_owners:
                continue
            additions = [
                upgrade
                for upgrade in candidates
                if any(setup_sid in supported_setups for setup_sid in upgrade.general_setup_sids)
            ]
            assignments.setdefault(technician_sid, []).extend(additions)

    lines = [
        "// AUTO-GENERATED - BPRUE upgrades follow each technician's effective Vanilla/DLC weapon support.",
        "// TechnicianNPC and AllTechnicianNPC receive the union of all BPRUE technician upgrades.",
        "// Concrete technicians keep their own assignments; all additions use bpatch + wildcard entries.",
        "",
    ]

    # Keep one occurrence per SID across all technician assignments while preserving
    # the first BaseGame -> DLC occurrence. The common technician prototypes receive
    # this complete union, matching the working reference mod's structure.
    all_upgrades = list({
        upgrade.sid: upgrade
        for upgrades in assignments.values()
        for upgrade in upgrades
    }.values())

    for common_sid in ("TechnicianNPC", "AllTechnicianNPC"):
        lines += [f"{common_sid} : struct.begin {{bpatch}}", "   Upgrades : struct.begin {bpatch}"]
        for upgrade in all_upgrades:
            lines += ["      [*] : struct.begin", f"         UpgradePrototypeSID = {upgrade.sid}", "         Enabled = true", "      struct.end"]
        lines += ["   struct.end", "struct.end", ""]

    for technician_sid, upgrades in assignments.items():
        if not upgrades:
            continue
        # Keep one occurrence per SID while preserving BaseGame -> DLC order.
        upgrades = list({upgrade.sid: upgrade for upgrade in upgrades}.values())
        lines += [
            f"{technician_sid} : struct.begin {{bpatch}}",
            "   Upgrades : struct.begin {bpatch}",
        ]
        for upgrade in upgrades:
            lines += ["      [*] : struct.begin", f"         UpgradePrototypeSID = {upgrade.sid}", "         Enabled = true", "      struct.end"]
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


