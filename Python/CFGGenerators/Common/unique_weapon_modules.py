from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel, UpgradeDefinition

CONFIG_PATH = Path(__file__).with_name("unique_weapons.json")

CLASS_CONFIG_KEYS = {
    "AssaultRifles": "ar",
    "SMGs": "smg",
    "Shotguns": "shotgun",
    "Pistols": "pistol",
    "Snipers": "sniper",
    "MachineGuns": "machine_gun",
}


def load_unique_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _unique_prefix(name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", name)
    return f"BPRUEUnique{token}"


def _clone_sid(source_sid: str, base_prefix: str, unique_prefix: str) -> str:
    if not source_sid.startswith(base_prefix):
        raise ValueError(f"Cannot clone {source_sid}: expected base prefix {base_prefix}")
    return unique_prefix + source_sid[len(base_prefix):]


def add_unique_modules(model: UpgradeBuildModel, configs: dict) -> int:
    """Clone every BPRUE module of each base family onto its Unique GeneralSetup.

    This runs after class-specific and shared modules have been built, so a Unique
    receives the complete BPRUE package of its base family (including stock/shared
    modules and existing family signatures) with fresh prototype SIDs. A later
    Unique-specific signature can be added without changing this mechanism.
    """
    unique_config = load_unique_config()
    source_by_setup = model.by_general_setup()
    added = 0

    for unique_name, unique in unique_config.get("uniques", {}).items():
        class_name = unique["class"]
        config_key = CLASS_CONFIG_KEYS.get(class_name)
        if not config_key or config_key not in configs:
            raise ValueError(f"{unique_name}: no loaded generator config for class {class_name}")
        class_config = configs[config_key]
        base_name = unique["base_family"]
        base = class_config.get("families", {}).get(base_name)
        if not base:
            raise ValueError(f"{unique_name}: unknown {class_name} base_family {base_name}")

        base_setup = base["general_setup_sid"]
        base_prefix = base["prototype_prefix"]
        source_upgrades = source_by_setup.get(base_setup, [])
        if not source_upgrades:
            raise ValueError(f"{unique_name}: base family {base_name} ({base_setup}) has no BPRUE upgrades")

        unique_setup = unique["general_setup_sid"]
        unique_prefix = unique.get("prototype_prefix", _unique_prefix(unique_name))
        sid_map = {u.sid: _clone_sid(u.sid, base_prefix, unique_prefix) for u in source_upgrades}

        for source in source_upgrades:
            cloned = replace(
                source,
                sid=sid_map[source.sid],
                general_setup_sid=unique_setup,
                additional_general_setup_sids=(),
                blocking_sids=tuple(sid_map.get(sid, sid) for sid in source.blocking_sids),
                horizontal_position=None,
            )
            model.add(cloned)
            added += 1

    return added
