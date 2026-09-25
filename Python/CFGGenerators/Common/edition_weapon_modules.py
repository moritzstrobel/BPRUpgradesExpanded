from __future__ import annotations

import json
from pathlib import Path

from dlc_weapon_modules import build_content_pack_models
from upgrade_build_model import UpgradeBuildModel

CONFIG_PATH = Path(__file__).with_name("edition_weapons.json")


def load_edition_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def build_edition_models(source_model: UpgradeBuildModel, configs: dict) -> dict[str, UpgradeBuildModel]:
    """Build optional Deluxe/PreOrder/Ultimate models.

    Edition content uses the game's DLCGameData/<pack> namespace, but is kept
    separate from the story-DLC configuration and output lifecycle in BPRUE.
    """
    return build_content_pack_models(
        source_model,
        configs,
        load_edition_config().get("weapons", {}),
        include_signatures=False,
    )
