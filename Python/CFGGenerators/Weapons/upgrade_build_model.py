from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class UpgradeDefinition:
    """One generated BPRUE upgrade and every place that must reference it."""

    sid: str
    general_setup_sid: str
    weapon_class: str
    group: str
    target_part: str
    text_sid: str
    hint_sid: str
    image: str
    icon: str
    cost: int
    effects: tuple[str, ...] = ()
    blocking_sids: tuple[str, ...] = ()
    vertical_position: str | None = None
    technician: bool = True
    template_sid: str | None = None
    horizontal_position: int | None = None


@dataclass
class UpgradeBuildModel:
    """Complete in-memory source of truth for generated weapon upgrades."""

    upgrades: list[UpgradeDefinition] = field(default_factory=list)

    def add(self, upgrade: UpgradeDefinition) -> None:
        self.upgrades.append(upgrade)

    def extend(self, upgrades: Iterable[UpgradeDefinition]) -> None:
        self.upgrades.extend(upgrades)

    def validate(self) -> None:
        errors: list[str] = []
        by_sid: dict[str, UpgradeDefinition] = {}

        for upgrade in self.upgrades:
            previous = by_sid.get(upgrade.sid)
            if previous is not None:
                errors.append(
                    f"duplicate upgrade SID {upgrade.sid}: "
                    f"{previous.general_setup_sid} / {upgrade.general_setup_sid}"
                )
            else:
                by_sid[upgrade.sid] = upgrade

            if not upgrade.general_setup_sid:
                errors.append(f"{upgrade.sid}: missing GeneralSetup SID")
            if not upgrade.target_part:
                errors.append(f"{upgrade.sid}: missing UpgradeTargetPart")
            if not upgrade.effects:
                errors.append(f"{upgrade.sid}: no effects configured")

        known = set(by_sid)
        for upgrade in self.upgrades:
            unknown_blocks = [sid for sid in upgrade.blocking_sids if sid not in known]
            if unknown_blocks:
                errors.append(
                    f"{upgrade.sid}: BlockingUpgradePrototypeSIDs not generated: "
                    + ", ".join(unknown_blocks)
                )

        if errors:
            raise ValueError("Invalid BPRUE upgrade build model:\n  - " + "\n  - ".join(errors))

    def by_general_setup(self) -> dict[str, list[UpgradeDefinition]]:
        result: dict[str, list[UpgradeDefinition]] = {}
        for upgrade in self.upgrades:
            result.setdefault(upgrade.general_setup_sid, []).append(upgrade)
        return result

    def technician_upgrades(self) -> list[UpgradeDefinition]:
        return [upgrade for upgrade in self.upgrades if upgrade.technician]

    def summary(self) -> str:
        classes: dict[str, int] = {}
        for upgrade in self.upgrades:
            classes[upgrade.weapon_class] = classes.get(upgrade.weapon_class, 0) + 1
        detail = ", ".join(f"{name}={count}" for name, count in sorted(classes.items()))
        return f"{len(self.upgrades)} upgrades ({detail})"
