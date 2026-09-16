from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path

from upgrade_build_model import UpgradeBuildModel

CONFIG_PATH = Path(__file__).with_name("dlc_weapons.json")

CLASS_CONFIG_KEYS = {
    "AssaultRifles": "ar",
    "SMGs": "smg",
    "Shotguns": "shotgun",
    "Pistols": "pistol",
    "Snipers": "sniper",
    "MachineGuns": "machine_gun",
}


def load_dlc_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _dlc_prefix(pack: str, name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]", "", f"{pack}{name}")
    return f"BPRUEDLC{token}"


def _clone_sid(source_sid: str, base_prefix: str, dlc_prefix: str) -> str:
    if not source_sid.startswith(base_prefix):
        raise ValueError(f"Cannot clone {source_sid}: expected base prefix {base_prefix}")
    return dlc_prefix + source_sid[len(base_prefix):]


def build_dlc_models(source_model: UpgradeBuildModel, configs: dict) -> dict[str, UpgradeBuildModel]:
    """Clone BPRUE base-family modules into one isolated model per DLC content pack.

    The returned models are deliberately separate from the base-game model. This
    guarantees that DLC GeneralSetup patches can later be rendered into their own
    DLCGameData/<pack> paths instead of leaking into GameLite/GameData output.
    """
    result: dict[str, UpgradeBuildModel] = {}
    source_by_setup = source_model.by_general_setup()

    for name, weapon in load_dlc_config().get("weapons", {}).items():
        pack = weapon["content_pack"]
        class_name = weapon["class"]
        config_key = CLASS_CONFIG_KEYS.get(class_name)
        if not config_key or config_key not in configs:
            raise ValueError(f"{pack}/{name}: no loaded generator config for class {class_name}")

        class_config = configs[config_key]
        base_name = weapon["base_family"]
        base = class_config.get("families", {}).get(base_name)
        if not base:
            raise ValueError(f"{pack}/{name}: unknown {class_name} base_family {base_name}")

        base_setup = base["general_setup_sid"]
        base_prefix = base["prototype_prefix"]
        source_upgrades = source_by_setup.get(base_setup, [])
        if not source_upgrades:
            raise ValueError(f"{pack}/{name}: base family {base_name} ({base_setup}) has no BPRUE upgrades")

        target_setup = weapon["general_setup_sid"]
        prefix = weapon.get("prototype_prefix", _dlc_prefix(pack, name))
        sid_map = {upgrade.sid: _clone_sid(upgrade.sid, base_prefix, prefix) for upgrade in source_upgrades}
        target_model = result.setdefault(pack, UpgradeBuildModel())

        for source in source_upgrades:
            target_model.add(replace(
                source,
                sid=sid_map[source.sid],
                general_setup_sid=target_setup,
                additional_general_setup_sids=(),
                blocking_sids=tuple(sid_map.get(sid, sid) for sid in source.blocking_sids),
                horizontal_position=None,
            ))

    for model in result.values():
        model.validate()
    return result
