from __future__ import annotations

"""Build all shared BPRUE specialization modules for the unified generator."""

from specialization_modules import build_shared_specializations


def build_shared_upgrades(configs: dict) -> list:
    result = []

    # Imports are intentionally local. generate_all_cfg adds Common to sys.path
    # before importing this module, while the class generators remain regular
    # CFGGenerators namespace modules.
    from CFGGenerators.AssaultRifles import generate_assault_rifle_upgrades as ar
    from CFGGenerators.MachineGuns import generate_machine_gun_upgrades as machine_gun
    from CFGGenerators.Pistols import generate_pistol_upgrades as pistol
    from CFGGenerators.Shotguns import generate_shotgun_upgrades as shotgun
    from CFGGenerators.SMGs import generate_smg_upgrades as smg
    from CFGGenerators.Snipers import generate_sniper_upgrades as sniper

    result.extend(build_shared_specializations(
        families=configs["pistol"]["families"],
        class_key="pistol", weapon_class="Pistol",
        template_sid=pistol.TEMPLATE_SID,
        image_for_family=lambda _: pistol.IMAGE,
        icon=pistol.ICON, sid_namespace="PistolShared",
    ))
    result.extend(build_shared_specializations(
        families=configs["smg"]["families"],
        class_key="smg", weapon_class="SMG",
        template_sid=smg.TEMPLATE_SID,
        image_for_family=lambda _: smg.IMAGE,
        icon=smg.ICON, sid_namespace="SMGShared",
    ))
    result.extend(build_shared_specializations(
        families=configs["ar"]["families"],
        class_key="assault_rifle", weapon_class="AR",
        template_sid=ar.MODULE_TEMPLATE_SID,
        image_for_family=lambda family: family["image"],
        icon=ar.DEFAULT_ICON, sid_namespace="ARShared",
    ))
    result.extend(build_shared_specializations(
        families=configs["shotgun"]["families"],
        class_key="shotgun", weapon_class="SG",
        template_sid=shotgun.TEMPLATE_SID,
        image_for_family=lambda _: shotgun.IMAGE,
        icon=shotgun.ICON, sid_namespace="SGShared",
    ))
    result.extend(build_shared_specializations(
        families=configs["sniper"]["families"],
        class_key="sniper", weapon_class="Sniper",
        template_sid=sniper.TEMPLATE_SID,
        image_for_family=lambda _: sniper.IMAGE,
        icon=sniper.ICON, sid_namespace="SniperShared",
    ))
    result.extend(build_shared_specializations(
        families=configs["machine_gun"]["families"],
        class_key="machine_gun", weapon_class="MG",
        template_sid=machine_gun.TEMPLATE_SID,
        image_for_family=lambda _: machine_gun.IMAGE,
        icon=machine_gun.ICON, sid_namespace="MGShared",
    ))

    return result


__all__ = ["build_shared_upgrades"]
