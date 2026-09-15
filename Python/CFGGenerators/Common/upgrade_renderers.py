from __future__ import annotations

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition
from vanilla_upgrade_layout import vanilla_general_setup_upgrades

TECHNICIAN_SIDS = (
    "TechnicianNPC", "AllTechnicianNPC", "Linza", "Konder", "Hors", "Stepsel",
    "SerzEremeev", "nikolaj", "laborant_aupova", "serzdot_eremeev_0", "kovyraska_0",
    "multik_0", "semenyc_0", "serzant_ivajlov_0", "serzant_hmaruk_0", "garpia_0",
    "Surup", "medlak_0", "PowerPlug_Pripyat", "serz_ivaj_0", "supack_technician_banzaj_0",
)


def _render_upgrade(upgrade: UpgradeDefinition, fallback_template: str | None = None) -> list[str]:
    template = upgrade.template_sid or fallback_template
    if not template:
        raise ValueError(f"{upgrade.sid}: no template SID configured")
    lines = [
        f"{upgrade.sid} : struct.begin {{refkey={template}}}",
        f"   SID = {upgrade.sid}", f"   Text = {upgrade.text_sid}", f"   Hint = {upgrade.hint_sid}",
        f"   Image = {upgrade.image}", f"   Icon = {upgrade.icon}", f"   BaseCost = {upgrade.cost}",
    ]
    if upgrade.horizontal_position is not None:
        lines.append(f"   HorizontalPosition = {upgrade.horizontal_position}")
    if upgrade.vertical_position is not None:
        lines.append(f"   VerticalPosition = EUpgradeVerticalPosition::{upgrade.vertical_position}")
    lines.append(f"   UpgradeTargetPart = EUpgradeTargetPartType::{upgrade.target_part}")
    if upgrade.effects:
        lines.append("   EffectPrototypeSIDs : struct.begin")
        lines += [f"      [{index}] = {effect}" for index, effect in enumerate(upgrade.effects)]
        lines.append("   struct.end")
    if upgrade.blocking_sids:
        lines.append("   BlockingUpgradePrototypeSIDs : struct.begin")
        lines += [f"      [{index}] = {sid}" for index, sid in enumerate(upgrade.blocking_sids)]
        lines.append("   struct.end")
    lines += ["struct.end", ""]
    return lines


def render_upgrade_prototypes(model: UpgradeBuildModel, *, source: str, template_sid: str, header_comments: tuple[str, ...] = ()) -> str:
    lines = [f"// AUTO-GENERATED - Source: {source} via UpgradeBuildModel"]
    lines.extend(f"// {comment}" for comment in header_comments)
    lines += ["", f"{template_sid} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}", f"   SID = {template_sid}", "   IsModification = true", "struct.end", ""]
    for upgrade in model.upgrades:
        lines += _render_upgrade(upgrade, template_sid)
    return "\n".join(lines)


def render_consolidated_upgrade_prototypes(model: UpgradeBuildModel) -> str:
    lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// Final BPRUE weapon upgrade graph rendered directly from UpgradeBuildModel.", "// -----------------------------------------------------------------------------", ""]
    templates = list(dict.fromkeys(upgrade.template_sid for upgrade in model.upgrades if upgrade.template_sid))
    for template in templates:
        lines += [f"{template} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}", f"   SID = {template}", "   IsModification = true", "struct.end", ""]
    for upgrade in model.upgrades:
        lines += _render_upgrade(upgrade)
    return "\n".join(lines).rstrip() + "\n"


def render_general_setup_patch(model: UpgradeBuildModel, *, header_comments: tuple[str, ...] = ()) -> str:
    lines = ["// AUTO-GENERATED - Source: UpgradeBuildModel"]
    lines.extend(f"// {comment}" for comment in header_comments)
    lines.append("")
    for general_setup_sid, upgrades in model.by_general_setup().items():
        lines.append(f"{general_setup_sid} : struct.begin {{bpatch}}")
        for name, value in model.general_setup_properties(general_setup_sid):
            lines.append(f"   {name} = {value}")
        lines.append("   UpgradePrototypeSIDs : struct.begin {bpatch}")
        lines += [f"      [*] = {upgrade.sid}" for upgrade in upgrades]
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines)


def render_final_general_setup_patch(model: UpgradeBuildModel, attachment_blocks: dict[str, list[str]] | None = None) -> str:
    vanilla = vanilla_general_setup_upgrades()
    attachments = attachment_blocks or {}
    lines = ["// -----------------------------------------------------------------------------", "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND", "// UpgradePrototypeSIDs are one complete indexed Vanilla + BPRUE array.", "// -----------------------------------------------------------------------------", ""]
    for setup_sid, upgrades in model.by_general_setup().items():
        if setup_sid not in vanilla:
            raise ValueError(f"No vanilla UpgradePrototypeSIDs found for {setup_sid}")
        combined = list(dict.fromkeys([*vanilla[setup_sid], *(upgrade.sid for upgrade in upgrades)]))
        lines.append(f"{setup_sid} : struct.begin {{bpatch}}")
        for name, value in model.general_setup_properties(setup_sid):
            lines.append(f"   {name} = {value}")
        lines.append("   UpgradePrototypeSIDs : struct.begin")
        lines += [f"      [{index}] = {sid}" for index, sid in enumerate(combined)]
        lines.append("   struct.end")
        lines += attachments.get(setup_sid, [])
        lines += ["struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"


def render_technician_patch(model: UpgradeBuildModel) -> str:
    upgrades = model.technician_upgrades()
    lines = ["// AUTO-GENERATED - all BPRUE weapon specialization modules are available at all technicians.", ""]
    for technician_sid in TECHNICIAN_SIDS:
        lines += [f"{technician_sid} : struct.begin {{bpatch}}", "   Upgrades : struct.begin {bpatch}"]
        for upgrade in upgrades:
            lines += ["      [*] : struct.begin", f"         UpgradePrototypeSID = {upgrade.sid}", "         Enabled = true", "      struct.end"]
        lines += ["   struct.end", "struct.end", ""]
    return "\n".join(lines).rstrip() + "\n"
