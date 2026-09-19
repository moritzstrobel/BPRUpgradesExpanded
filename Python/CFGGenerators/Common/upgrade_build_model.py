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
    required_upgrade_sids: tuple[str, ...] = ()
    vertical_position: str | None = None
    technician: bool = True
    template_sid: str | None = None
    horizontal_position: int | None = None
    additional_general_setup_sids: tuple[str, ...] = ()
    require_effects: bool = True
    # Standalones are packed only after normal grouped rows. They may fill any
    # remaining visible cell instead of reserving a complete horizontal column.
    standalone: bool = False

    @property
    def general_setup_sids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((self.general_setup_sid, *self.additional_general_setup_sids)))


@dataclass(frozen=True)
class GeneralSetupDefinition:
    """Additional properties that belong to a weapon GeneralSetup patch."""

    sid: str
    properties: tuple[tuple[str, str], ...] = ()


@dataclass
class UpgradeBuildModel:
    """Complete in-memory source of truth for generated weapon upgrades."""

    upgrades: list[UpgradeDefinition] = field(default_factory=list)
    general_setups: dict[str, GeneralSetupDefinition] = field(default_factory=dict)

    def add(self, upgrade: UpgradeDefinition) -> None:
        self.upgrades.append(upgrade)

    def extend(self, upgrades: Iterable[UpgradeDefinition]) -> None:
        self.upgrades.extend(upgrades)

    def configure_general_setup(self, sid: str, **properties: object) -> None:
        normalized = tuple((name, str(value)) for name, value in properties.items() if value is not None)
        definition = GeneralSetupDefinition(sid=sid, properties=normalized)
        previous = self.general_setups.get(sid)
        if previous is not None and previous != definition:
            raise ValueError(f"conflicting GeneralSetup configuration for {sid}")
        self.general_setups[sid] = definition

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
            if any(not sid for sid in upgrade.general_setup_sids):
                errors.append(f"{upgrade.sid}: empty GeneralSetup SID")
            if not upgrade.target_part:
                errors.append(f"{upgrade.sid}: missing UpgradeTargetPart")
            if upgrade.require_effects and not upgrade.effects:
                errors.append(f"{upgrade.sid}: no effects configured")
            if upgrade.horizontal_position is not None and not 0 <= upgrade.horizontal_position <= 2:
                errors.append(f"{upgrade.sid}: invisible HorizontalPosition H{upgrade.horizontal_position}")

        known = set(by_sid)
        for upgrade in self.upgrades:
            unknown_requirements = [sid for sid in upgrade.required_upgrade_sids if sid not in known]
            if unknown_requirements:
                errors.append(
                    f"{upgrade.sid}: RequiredUpgradePrototypeSIDs not generated: "
                    + ", ".join(unknown_requirements)
                )
            unknown_blocks = [sid for sid in upgrade.blocking_sids if sid not in known]
            if unknown_blocks:
                errors.append(
                    f"{upgrade.sid}: BlockingUpgradePrototypeSIDs not generated: "
                    + ", ".join(unknown_blocks)
                )

        configured_without_upgrades = set(self.general_setups) - set(self.by_general_setup())
        for sid in sorted(configured_without_upgrades):
            errors.append(f"{sid}: GeneralSetup configured but has no generated upgrades")

        if errors:
            raise ValueError("Invalid BPRUE upgrade build model:\n  - " + "\n  - ".join(errors))

    def by_general_setup(self) -> dict[str, list[UpgradeDefinition]]:
        result: dict[str, list[UpgradeDefinition]] = {}
        for upgrade in self.upgrades:
            for sid in upgrade.general_setup_sids:
                result.setdefault(sid, []).append(upgrade)
        return result

    def general_setup_properties(self, sid: str) -> tuple[tuple[str, str], ...]:
        definition = self.general_setups.get(sid)
        return definition.properties if definition else ()

    def technician_upgrades(self) -> list[UpgradeDefinition]:
        return [upgrade for upgrade in self.upgrades if upgrade.technician]

    def summary(self) -> str:
        classes: dict[str, int] = {}
        for upgrade in self.upgrades:
            classes[upgrade.weapon_class] = classes.get(upgrade.weapon_class, 0) + 1
        detail = ", ".join(f"{name}={count}" for name, count in sorted(classes.items()))
        return f"{len(self.upgrades)} upgrades ({detail})"
