from __future__ import annotations

from upgrade_build_model import UpgradeBuildModel


def render_upgrade_prototypes(
    model: UpgradeBuildModel,
    *,
    source: str,
    template_sid: str,
    header_comments: tuple[str, ...] = (),
) -> str:
    lines = [f"// AUTO-GENERATED - Source: {source} via UpgradeBuildModel"]
    lines.extend(f"// {comment}" for comment in header_comments)
    lines += [
        "",
        f"{template_sid} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}",
        f"   SID = {template_sid}",
        "   IsModification = true",
        "struct.end",
        "",
    ]

    for upgrade in model.upgrades:
        lines += [
            f"{upgrade.sid} : struct.begin {{refkey={upgrade.template_sid or template_sid}}}",
            f"   SID = {upgrade.sid}",
            f"   Text = {upgrade.text_sid}",
            f"   Hint = {upgrade.hint_sid}",
            f"   Image = {upgrade.image}",
            f"   Icon = {upgrade.icon}",
            f"   BaseCost = {upgrade.cost}",
        ]
        if upgrade.horizontal_position is not None:
            lines.append(f"   HorizontalPosition = {upgrade.horizontal_position}")
        if upgrade.vertical_position is not None:
            lines.append(f"   VerticalPosition = EUpgradeVerticalPosition::{upgrade.vertical_position}")
        lines += [
            f"   UpgradeTargetPart = EUpgradeTargetPartType::{upgrade.target_part}",
            "   EffectPrototypeSIDs : struct.begin",
        ]
        lines += [f"      [{index}] = {effect}" for index, effect in enumerate(upgrade.effects)]
        lines.append("   struct.end")
        if upgrade.blocking_sids:
            lines.append("   BlockingUpgradePrototypeSIDs : struct.begin")
            lines += [f"      [{index}] = {sid}" for index, sid in enumerate(upgrade.blocking_sids)]
            lines.append("   struct.end")
        lines += ["struct.end", ""]

    return "\n".join(lines)


def render_general_setup_patch(
    model: UpgradeBuildModel,
    *,
    header_comments: tuple[str, ...] = (),
) -> str:
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
