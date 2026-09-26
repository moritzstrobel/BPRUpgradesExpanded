from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
ARMOR_ROOT = CONTENT_ROOT / "Armor"
ARMOR_GAME_ROOT = ARMOR_ROOT / "GameLite"
CONFIG_PATH = SCRIPT_DIR / "armor_signatures.json"
MODULE_CONFIG_PATH = SCRIPT_DIR / "armor_modules.json"
CONTENT_PACK_CONFIG_PATH = SCRIPT_DIR / "armor_content_packs.json"
DLC_REFERENCE_ROOT = PYTHON_ROOT / "VanillaReference" / "DLCGameData"
CLASSIFICATION_PATH = PYTHON_ROOT / "AnalysisArmor" / "Reports" / "armor_classification.json"
UPGRADE_MAPPING_PATH = PYTHON_ROOT / "AnalysisArmor" / "Reports" / "armor_upgrade_mapping.json"
UPGRADE_DETAILS_PATH = PYTHON_ROOT / "AnalysisArmor" / "Reports" / "armor_upgrade_details.json"
MAX_VISIBLE_HORIZONTAL_POSITION = 2
VERTICALS = ("Top", "Down", None)
ARMOR_TARGET_ORDER = ("Body", "Barrel", "Handguard", "PistolGrip", "Stock")

ARMOR_PATCH_PATH = ARMOR_GAME_ROOT / "GameData/ItemPrototypes/ArmorPrototypes/ArmorPrototypes_patch_BPRUE_Armor.cfg"
UPGRADE_OUTPUT_PATH = ARMOR_GAME_ROOT / "GameData/UpgradePrototypes/UpgradePrototypes_patch_BPRUE_Armor.cfg"
EFFECT_OUTPUT_PATH = ARMOR_GAME_ROOT / "GameData/EffectPrototypes/EffectPrototypes_patch_BPRUE_Armor.cfg"
NPC_OUTPUT_PATH = ARMOR_GAME_ROOT / "GameData/NPCPrototypes/NPCPrototypes_patch_BPRUE_Armor.cfg"
VANILLA_NPC_PATH = PYTHON_ROOT / "VanillaReference" / "NPCPrototypes.cfg"

MODULE_TEMPLATE_SID = "BPRUE_ArmorModuleTemplate"
FACTION_IMAGES = {
    "BANDIT": "Bandits",
    "DUTY": "Duty",
    "ECOLOGIST": "Ekolog",
    "FREEDOM": "Freedom",
    "FREE_STALKER": "Loners",
    "MERCENARY": "Mercs",
    "MILITARY": "Military",
    "MONOLITH": "Monolith",
    "SPARK": "Spark",
    "WARD": "Ward",
}


def faction_module_image(faction: str) -> str:
    asset_suffix = FACTION_IMAGES.get(faction)
    if asset_suffix is None:
        raise ValueError(f"No armor module image configured for faction {faction}")
    asset = f"T_Module_Armor_{asset_suffix}"
    return (
        "Texture2D'/BPRUpgradesExpanded/GameLite/FPS_Game/UIRemaster/"
        f"UITextures/PDA/Upgrades/Armor/{asset}.{asset}'"
    )


BPRUE_MODULE_IMAGE = "Texture2D'/BPRUpgradesExpanded/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/T_Module_Base.T_Module_Base'"
DEFAULT_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/Armor/T_PDA_Upgrades_Icon_AttachmentSystem.T_PDA_Upgrades_Icon_AttachmentSystem'"


ARMOR_EFFECT_UI = {
    "ProtectionStrike": ("armor_protectionPhysical", "Strike Protection"),
    "ProtectionBurn": ("armor_protectionThermal", "Thermal Protection"),
    "ProtectionShock": ("armor_protectionElectrical", "Electrical Protection"),
    "ProtectionChemical": ("armor_protectionChemical", "Chemical Protection"),
    "ProtectionRadiation": ("armor_protectionRadiation", "Radiation Protection"),
    "ArmorItemWeight": ("armor_reductionWeight", "Item Weight"),
    "MaxDurability": ("armor_wearing", "Max Durability"),
    "RegenStamina": ("Armor_regenerationStamina", "Regen Stamina"),
    "Composite": ("Armor_carryingCapacity", "Carrying Capacity"),
    "AdditionalInventoryWeight": ("increase_max_inventory_weight", "Increase max inventory weight"),
    "DegenBleeding": ("general_protectionBleed", "Bleeding Protection"),
}


@dataclass(frozen=True)
class ArmorUpgradeDefinition:
    sid: str
    armor_sid: str
    faction: str
    category: str
    signature: str
    target_part: str
    text_sid: str
    hint_sid: str
    cost: int
    effects: tuple[str, ...]
    tier_index: int
    family: str
    image: str | None = None
    blocking_sids: tuple[str, ...] = ()
    required_upgrade_sid: str | None = None
    horizontal_position: int | None = None
    vertical_position: str | None = None
    content_pack: str | None = None
    base_armor_sid: str | None = None


def load_config() -> dict:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    module_config = json.loads(MODULE_CONFIG_PATH.read_text(encoding="utf-8"))
    config["generic_modules"] = module_config["modules"]
    return config


def load_classification() -> dict:
    if not CLASSIFICATION_PATH.exists():
        raise FileNotFoundError(
            f"{CLASSIFICATION_PATH} missing; run Python/AnalysisArmor/classify_armor.py first"
        )
    return json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))



def load_content_pack_armors() -> list[dict]:
    """Load explicitly mapped Edition armors and their authored Vanilla upgrade arrays."""
    import re
    config = json.loads(CONTENT_PACK_CONFIG_PATH.read_text(encoding="utf-8"))
    result: list[dict] = []
    for pack, armors in config["packs"].items():
        source = DLC_REFERENCE_ROOT / pack / "ItemPrototypes.cfg"
        text = source.read_text(encoding="utf-8")
        for armor in armors:
            sid = armor["sid"]
            start_match = re.search(rf"(?m)^\\s*{re.escape(sid)}\\s*:\\s*struct\\.begin[^\\n]*$", text)
            if not start_match:
                raise ValueError(f"{pack}: armor prototype {sid} not found in {source}")
            start = start_match.start(); depth = 0; end = None
            for match in re.finditer(r"struct\\.begin|struct\\.end", text[start:]):
                depth += 1 if match.group(0) == "struct.begin" else -1
                if depth == 0:
                    end = start + match.end(); break
            if end is None:
                raise ValueError(f"{pack}: unterminated armor prototype {sid}")
            block = text[start:end]
            array = re.search(r"UpgradePrototypeSIDs\\s*:\\s*struct\\.begin(.*?)struct\\.end", block, re.S)
            if not array:
                raise ValueError(f"{pack}: {sid} has no UpgradePrototypeSIDs array")
            upgrades = re.findall(r"(?m)^\\s*\\[\\d+\\]\\s*=\\s*(\\S+)\\s*$", array.group(1))
            if not upgrades:
                raise ValueError(f"{pack}: {sid} has an empty UpgradePrototypeSIDs array")
            result.append({**armor, "pack": pack, "upgrades": upgrades})
    return result

def build_upgrades(config: dict | None = None, classification: dict | None = None) -> list[ArmorUpgradeDefinition]:
    config = config or load_config()
    classification = classification or load_classification()
    result: list[ArmorUpgradeDefinition] = []

    for faction, faction_cfg in config["prototype_factions"].items():
        if not faction_cfg.get("enabled", True):
            continue
        category_cfgs = faction_cfg["categories"]
        for armor in classification["factions"].get(faction, []):
            category = armor["category"]
            category_cfg = category_cfgs.get(category)
            if category_cfg is None:
                continue
            armor_sid = armor["sid"]
            previous_sid: str | None = None
            for tier_index, tier_cfg in enumerate(category_cfg["tiers"]):
                tier_id = tier_cfg["id"]
                sid = f"{armor_sid}_Upgrade_BPRUE_{faction}_{tier_id}"
                result.append(ArmorUpgradeDefinition(
                    sid=sid,
                    armor_sid=armor_sid,
                    faction=faction,
                    category=category,
                    signature=faction_cfg["signature"],
                    target_part=category_cfg["target_part"],
                    text_sid=tier_cfg["text_sid"],
                    hint_sid=tier_cfg["hint_sid"],
                    cost=int(tier_cfg["cost"]),
                    effects=tuple(tier_cfg["effects"]),
                    tier_index=tier_index,
                    family=f"FACTION:{faction}",
                    image=faction_module_image(faction),
                    required_upgrade_sid=previous_sid,
                ))
                previous_sid = sid

    content_pack_armors = load_content_pack_armors()
    for armor in content_pack_armors:
        faction = armor["faction"]
        faction_cfg = config["prototype_factions"][faction]
        category = armor["category"]
        category_cfg = faction_cfg["categories"].get(category)
        if category_cfg is None:
            continue
        previous_sid: str | None = None
        for tier_index, tier_cfg in enumerate(category_cfg["tiers"]):
            sid = f'{armor["sid"]}_Upgrade_BPRUE_{faction}_{tier_cfg["id"]}'
            result.append(ArmorUpgradeDefinition(
                sid=sid, armor_sid=armor["sid"], faction=faction, category=category,
                signature=faction_cfg["signature"], target_part=category_cfg["target_part"],
                text_sid=tier_cfg["text_sid"], hint_sid=tier_cfg["hint_sid"], cost=int(tier_cfg["cost"]),
                effects=tuple(tier_cfg["effects"]), tier_index=tier_index, family=f"FACTION:{faction}",
                image=faction_module_image(faction), required_upgrade_sid=previous_sid,
                content_pack=armor["pack"], base_armor_sid=armor["base_armor_sid"],
            ))
            previous_sid = sid

    # Generic faction-agnostic modules: one independent trade-off upgrade per armor.
    generic_armors = [armor for faction_armors in classification["factions"].values() for armor in faction_armors]
    generic_armors += load_content_pack_armors()
    for armor in generic_armors:
        category = armor["category"]
        armor_sid = armor["sid"]
        for module_id, module_cfg in config.get("generic_modules", {}).items():
            category_effects = module_cfg["effects"].get(category)
            if not category_effects:
                continue
            effect_sids = []
            for index, effect in enumerate(category_effects):
                effect_sids.append(f"BPRUE_Armor_Generic_{module_id}_{category}_Effect_{index + 1}")
            module_slug = module_id.title().replace("_", "")
            result.append(ArmorUpgradeDefinition(
                sid=f"{armor_sid}_Upgrade_BPRUE_GENERIC_{module_slug}",
                armor_sid=armor_sid,
                faction="GENERIC",
                category=category,
                signature="Generic",
                target_part="Body",
                text_sid=f"sid_bprue_armor_generic_{module_id.lower()}_name",
                hint_sid=f"sid_bprue_armor_generic_{module_id.lower()}_{category.lower()}_description",
                cost=int(module_cfg["cost"][category]),
                effects=tuple(effect_sids),
                tier_index=0,
                family=f"GENERIC:{module_cfg['group']}",
                image=BPRUE_MODULE_IMAGE,
                content_pack=armor.get("pack"),
                base_armor_sid=armor.get("base_armor_sid"),
            ))

    # Generic modules are mutually exclusive only inside their authored trade-off group.
    from dataclasses import replace
    generic_groups: dict[tuple[str, str], list[ArmorUpgradeDefinition]] = {}
    for upgrade in result:
        if upgrade.family.startswith("GENERIC:"):
            generic_groups.setdefault((upgrade.armor_sid, upgrade.family), []).append(upgrade)
    blocked_result: list[ArmorUpgradeDefinition] = []
    for upgrade in result:
        if upgrade.family.startswith("GENERIC:"):
            siblings = tuple(
                sibling.sid
                for sibling in generic_groups[(upgrade.armor_sid, upgrade.family)]
                if sibling.sid != upgrade.sid
            )
            upgrade = replace(upgrade, blocking_sids=siblings)
        blocked_result.append(upgrade)
    result = blocked_result

    result = apply_layout(result)
    validate(result)
    return result


def _upgrade_details() -> dict:
    if not UPGRADE_DETAILS_PATH.exists():
        raise FileNotFoundError(
            f"{UPGRADE_DETAILS_PATH} missing; run Python/AnalysisArmor/analyze_armor_upgrades.py first"
        )
    data = json.loads(UPGRADE_DETAILS_PATH.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {row["sid"]: row for row in data}
    return data


def _vanilla_module_columns(armor_sid: str, vanilla_sids: list[str], details: dict) -> set[tuple[str, int]]:
    occupied: set[tuple[str, int]] = set()
    for sid in vanilla_sids:
        row = details.get(sid)
        if not row or not row.get("effective_is_modification"):
            continue
        target = row.get("effective_upgrade_target_part")
        if not target:
            continue
        target = target.rsplit("::", 1)[-1]
        raw_h = row.get("effective_horizontal_position")
        # Vanilla commonly omits HorizontalPosition. The engine treats that as H0,
        # so the allocator must reserve H0 as well.
        horizontal = int(raw_h) if raw_h is not None and str(raw_h).lstrip("-").isdigit() else 0
        if 0 <= horizontal <= MAX_VISIBLE_HORIZONTAL_POSITION:
            occupied.add((target, horizontal))
    return occupied

def _first_free_armor_column(preferred: str, occupied: set[tuple[str, int]]) -> tuple[str, int]:
    targets = (preferred, *(target for target in ARMOR_TARGET_ORDER if target != preferred))
    for target in targets:
        for horizontal in range(MAX_VISIBLE_HORIZONTAL_POSITION + 1):
            if (target, horizontal) not in occupied:
                return target, horizontal
    raise ValueError(f"No visible H0-H{MAX_VISIBLE_HORIZONTAL_POSITION} armor module column left")


def apply_layout(upgrades: list[ArmorUpgradeDefinition]) -> list[ArmorUpgradeDefinition]:
    from dataclasses import replace
    from collections import defaultdict

    vanilla_by_armor = _vanilla_upgrade_sids_by_armor()
    vanilla_by_armor.update({armor["sid"]: armor["upgrades"] for armor in load_content_pack_armors()})
    details = _upgrade_details()
    by_armor: dict[str, list[ArmorUpgradeDefinition]] = defaultdict(list)
    for upgrade in upgrades:
        by_armor[upgrade.armor_sid].append(upgrade)

    resolved: list[ArmorUpgradeDefinition] = []
    for armor_sid, tiers in by_armor.items():
        vanilla_sids = vanilla_by_armor.get(armor_sid)
        if vanilla_sids is None:
            raise ValueError(f"{armor_sid}: missing Vanilla UpgradePrototypeSIDs mapping")
        occupied = _vanilla_module_columns(armor_sid, vanilla_sids, details)
        families: dict[str, list[ArmorUpgradeDefinition]] = defaultdict(list)
        for upgrade in tiers:
            families[upgrade.family].append(upgrade)
        for family, family_upgrades in families.items():
            target, horizontal = _first_free_armor_column(family_upgrades[0].target_part, occupied)
            occupied.add((target, horizontal))
            ordered = (
                sorted(family_upgrades, key=lambda item: item.sid)
                if family.startswith("GENERIC:")
                else sorted(family_upgrades, key=lambda item: item.tier_index)
            )
            if len(ordered) > len(VERTICALS):
                raise ValueError(f"{armor_sid}: armor module family {family} exceeds {len(VERTICALS)} vertical slots")
            for index, upgrade in enumerate(ordered):
                vertical_index = index if family.startswith("GENERIC:") else upgrade.tier_index
                resolved.append(replace(
                    upgrade,
                    target_part=target,
                    horizontal_position=None if horizontal == 0 else horizontal,
                    vertical_position=VERTICALS[vertical_index],
                ))
    return resolved


def validate(upgrades: list[ArmorUpgradeDefinition]) -> None:
    seen: set[str] = set()
    errors: list[str] = []
    for upgrade in upgrades:
        if upgrade.sid in seen:
            errors.append(f"duplicate upgrade SID {upgrade.sid}")
        seen.add(upgrade.sid)
        if not upgrade.effects:
            errors.append(f"{upgrade.sid}: no effects")
        if upgrade.tier_index > 0 and not upgrade.required_upgrade_sid:
            errors.append(f"{upgrade.sid}: tier {upgrade.tier_index + 1} has no prerequisite")
    if errors:
        raise ValueError("Invalid BPRUE armor signature model:\n  - " + "\n  - ".join(errors))


def render_upgrade_fragment(upgrades: list[ArmorUpgradeDefinition]) -> str:
    lines = [
        "// -----------------------------------------------------------------------------",
        "// BPRUE ARMOR SIGNATURE UPGRADES",
        "// Generated by CFGGenerators/Armor/generate_armor_upgrades.py",
        "// Optional Armor module; follows Vanilla GameData prototype discovery.",
        "// -----------------------------------------------------------------------------",
        "",
        f"{MODULE_TEMPLATE_SID} : struct.begin {{refurl=@BaseGame/UpgradePrototypes.cfg;refkey=[0]}}",
        f"   SID = {MODULE_TEMPLATE_SID}",
        "   IsModification = true",
        "struct.end",
        "",
    ]
    for upgrade in upgrades:
        lines += [
            f"{upgrade.sid} : struct.begin {{refkey={MODULE_TEMPLATE_SID}}}",
            f"   SID = {upgrade.sid}",
            f"   Text = {upgrade.text_sid}",
            f"   Hint = {upgrade.hint_sid}",
            f"   Image = {upgrade.image or DEFAULT_ICON}",
            f"   Icon = {DEFAULT_ICON}",
            f"   BaseCost = {upgrade.cost}",
            *([f"   HorizontalPosition = {upgrade.horizontal_position}"] if upgrade.horizontal_position is not None else []),
            *([f"   VerticalPosition = EUpgradeVerticalPosition::{upgrade.vertical_position}"] if upgrade.vertical_position is not None else []),
            f"   UpgradeTargetPart = EUpgradeTargetPartType::{upgrade.target_part}",
            *([
                "   RequiredUpgradePrototypeSIDs : struct.begin",
                f"      [0] = {upgrade.required_upgrade_sid}",
                "   struct.end",
            ] if upgrade.required_upgrade_sid else []),
            "   EffectPrototypeSIDs : struct.begin",
            *(f"      [{i}] = {effect}" for i, effect in enumerate(upgrade.effects)),
            "   struct.end",
            *([
                "   BlockingUpgradePrototypeSIDs : struct.begin",
                *(f"      [{i}] = {sid}" for i, sid in enumerate(upgrade.blocking_sids)),
                "   struct.end",
            ] if upgrade.blocking_sids else []),
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _vanilla_upgrade_sids_by_armor() -> dict[str, list[str]]:
    if not UPGRADE_MAPPING_PATH.exists():
        raise FileNotFoundError(
            f"{UPGRADE_MAPPING_PATH} missing; run Python/AnalysisArmor/analyze_armor_upgrades.py first"
        )
    rows = json.loads(UPGRADE_MAPPING_PATH.read_text(encoding="utf-8"))
    return {row["sid"]: list(row["upgrades"]) for row in rows}


def render_armor_patch(upgrades: list[ArmorUpgradeDefinition]) -> str:
    by_armor: dict[str, list[ArmorUpgradeDefinition]] = {}
    for upgrade in upgrades:
        by_armor.setdefault(upgrade.armor_sid, []).append(upgrade)
        vanilla_by_armor = _vanilla_upgrade_sids_by_armor()
        vanilla_by_armor.update({armor["sid"]: armor["upgrades"] for armor in load_content_pack_armors()})
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Adds BPRUE faction signature modules to player armor without replacing",
        "// the armor's existing Vanilla UpgradePrototypeSIDs array.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for armor_sid, armor_upgrades in sorted(by_armor.items()):
        vanilla = vanilla_by_armor.get(armor_sid)
        if vanilla is None:
            raise ValueError(f"{armor_sid}: missing Vanilla UpgradePrototypeSIDs mapping")
        generated = [upgrade.sid for upgrade in sorted(armor_upgrades, key=lambda item: item.tier_index)]
        combined = list(dict.fromkeys([*vanilla, *generated]))
        lines += [
            f"{armor_sid} : struct.begin {{bpatch}}",
            "   UpgradePrototypeSIDs : struct.begin",
            *(f"      [{i}] = {sid}" for i, sid in enumerate(combined)),
            "   struct.end",
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _effect_value(value: object) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _render_effect(sid: str, spec: dict) -> list[str]:
    effect_type = spec["type"]
    value = _effect_value(spec["value"])
    show = bool(spec.get("show", True))
    lines = [
        f"{sid} : struct.begin {{refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}}",
        f"   SID = {sid}",
    ]
    localization_sid = spec.get("localization_sid")
    text = spec.get("text")
    if not localization_sid and effect_type in ARMOR_EFFECT_UI:
        localization_sid, default_text = ARMOR_EFFECT_UI[effect_type]
        text = text or default_text
    if localization_sid:
        lines.append(f"   LocalizationSID = {localization_sid}")
    if text:
        lines.append(f"   Text = {text}")
    lines += [
        f"   Type = EEffectType::{effect_type}",
        f"   ValueMin = {value}",
        f"   ValueMax = {value}",
    ]

    extra_effects = spec.get("extra_effects", [])
    if extra_effects:
        lines.append("   ApplyExtraEffectPrototypeSIDs : struct.begin")
        lines.extend(
            f"      [{index}] = {child['sid']}"
            for index, child in enumerate(extra_effects)
        )
        lines += [
            "   struct.end",
            "   ShouldPauseByDialog = false",
        ]
    else:
        lines.append("   bIsPermanent = true")
        if spec.get("positive"):
            lines.append(f"   Positive = EBeneficial::{spec['positive']}")

    lines += [
        f"   ShowUpgradeEffectValue = {'true' if show else 'false'}",
        f"   ShowUpgradeEffect = {'true' if show else 'false'}",
        "struct.end",
        "",
    ]
    return lines


def render_effects(config: dict | None = None) -> str:
    config = config or load_config()
    definitions = dict(config.get("effect_prototypes", {}))
    for module_id, module_cfg in config.get("generic_modules", {}).items():
        for category, effects in module_cfg["effects"].items():
            for index, spec in enumerate(effects):
                sid = f"BPRUE_Armor_Generic_{module_id}_{category}_Effect_{index + 1}"
                if spec["type"] == "Composite":
                    children = []
                    for child_index, child_type in enumerate(spec.get("composite", [])):
                        children.append({"sid": f"{sid}_Child_{child_index + 1}", "type": child_type, "value": spec["value"], "show": False, "positive": spec.get("positive")})
                    definitions[sid] = {"type": "Composite", "value": spec["value"], "show": True, "positive": spec.get("positive"), "extra_effects": children}
                else:
                    definitions[sid] = spec
    referenced = {
        effect_sid
        for faction_cfg in config["prototype_factions"].values()
        if faction_cfg.get("enabled", True)
        for category_cfg in faction_cfg["categories"].values()
        for tier_cfg in category_cfg["tiers"]
        for effect_sid in tier_cfg["effects"]
    }
    referenced.update(
        f"BPRUE_Armor_Generic_{module_id}_{category}_Effect_{index + 1}"
        for module_id, module_cfg in config.get("generic_modules", {}).items()
        for category, effects in module_cfg["effects"].items()
        for index, _ in enumerate(effects)
    )

    missing = sorted(referenced - set(definitions))
    if missing:
        raise ValueError(
            "Armor signature effects missing from effect_prototypes:\n  - "
            + "\n  - ".join(missing)
        )

    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// BPRUE Armor faction signature effects.",
        "// Source of truth: CFGGenerators/Armor/armor_signatures.json",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    rendered: set[str] = set()
    for sid in sorted(referenced):
        spec = definitions[sid]
        lines.extend(_render_effect(sid, spec))
        rendered.add(sid)
        for child in spec.get("extra_effects", []):
            child_sid = child["sid"]
            if child_sid in rendered:
                raise ValueError(f"Duplicate Armor effect SID {child_sid}")
            lines.extend(_render_effect(child_sid, child))
            rendered.add(child_sid)
    return "\n".join(lines).rstrip() + "\n"


def _parse_npc_blocks(text: str) -> dict[str, list[str]]:
    """Parse only depth-0 NPC structs and keep each complete nested block intact."""
    import re
    lines = text.splitlines()
    root_re = re.compile(r"^([A-Za-z0-9_.-]+)\s*:\s*struct\.begin(?:\s*\{[^}]*\})?\s*$")
    result: dict[str, list[str]] = {}
    index = 0

    while index < len(lines):
        match = root_re.match(lines[index])
        if not match:
            index += 1
            continue

        sid = match.group(1)
        start = index
        depth = 0
        while index < len(lines):
            line = lines[index]
            depth += len(re.findall(r"\bstruct\.begin\b", line))
            depth -= len(re.findall(r"\bstruct\.end\b", line))
            index += 1
            if depth == 0:
                break

        result[sid] = lines[start:index]

    return result


def _npc_refkey(block: list[str]) -> str | None:
    import re
    match = re.search(r"\{[^}]*refkey=([^;}]+)", block[0])
    return match.group(1).strip() if match else None


def _npc_type(block: list[str]) -> str | None:
    import re
    for line in block[1:]:
        match = re.match(r"\s*NPCType\s*=\s*(\S+)", line)
        if match:
            return match.group(1)
    return None


def _direct_npc_upgrade_sids(block: list[str]) -> list[str] | None:
    """Return the direct Upgrades array, or None when this NPC inherits it."""
    import re
    start = next((i for i, line in enumerate(block) if re.match(r"\s*Upgrades\s*:\s*struct\.begin", line)), None)
    if start is None:
        return None
    depth = 0
    result: list[str] = []
    for line in block[start:]:
        depth += line.count("struct.begin")
        depth -= 1 if line.strip() == "struct.end" else 0
        match = re.match(r"\s*UpgradePrototypeSID\s*=\s*(\S+)", line)
        if match and match.group(1) != "empty":
            result.append(match.group(1))
        if depth == 0:
            break
    return result


def _effective_npc_upgrade_sids(blocks: dict[str, list[str]], sid: str) -> list[str]:
    seen: set[str] = set()
    current = sid
    while current and current not in seen:
        seen.add(current)
        block = blocks.get(current)
        if not block:
            return []
        direct = _direct_npc_upgrade_sids(block)
        if direct is not None:
            return direct
        current = _npc_refkey(block)
    return []


def _effective_npc_type(blocks: dict[str, list[str]], sid: str) -> str | None:
    seen: set[str] = set()
    current = sid
    while current and current not in seen:
        seen.add(current)
        block = blocks.get(current)
        if not block:
            return None
        direct = _npc_type(block)
        if direct:
            return direct
        current = _npc_refkey(block)
    return None


def technician_armor_assignments(upgrades: list[ArmorUpgradeDefinition]) -> dict[str, list[ArmorUpgradeDefinition]]:
    """Give a technician BPRUE armor upgrades when their effective Vanilla list supports that armor."""
    if not VANILLA_NPC_PATH.exists():
        raise FileNotFoundError(VANILLA_NPC_PATH)
    blocks = _parse_npc_blocks(VANILLA_NPC_PATH.read_text(encoding="utf-8"))
    vanilla_by_armor = _vanilla_upgrade_sids_by_armor()
    content_pack_armors = load_content_pack_armors()
    vanilla_by_armor.update({armor["sid"]: armor["upgrades"] for armor in content_pack_armors})
    base_by_armor = {armor["sid"]: armor["base_armor_sid"] for armor in content_pack_armors}
    vanilla_sets = {armor: set(sids) for armor, sids in vanilla_by_armor.items()}

    assignments: dict[str, list[ArmorUpgradeDefinition]] = {}
    for technician_sid in blocks:
        if technician_sid in {"TechnicianNPC", "AllTechnicianNPC"}:
            continue
        if _effective_npc_type(blocks, technician_sid) != "ENPCType::Technician":
            continue
        supported = set(_effective_npc_upgrade_sids(blocks, technician_sid))
        selected = [
            upgrade for upgrade in upgrades
            # Armor mappings can contain shared/global upgrade SIDs (for example
            # FaustPsyResist_Quest_1_1).  Those must not make every armor look
            # supported by a technician.  Require at least one armor-owned
            # Vanilla SID instead.
            if supported.intersection(
                sid for sid in vanilla_sets.get(upgrade.armor_sid, set())
                if sid.startswith(f"{base_by_armor.get(upgrade.armor_sid, upgrade.armor_sid)}_")
            )
        ]
        if selected:
            assignments[technician_sid] = selected
    return assignments


def render_npc_patch(upgrades: list[ArmorUpgradeDefinition]) -> str:
    assignments = technician_armor_assignments(upgrades)
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// BPRUE Armor upgrades follow each technician's effective Vanilla armor support.",
        "// Standalone named lists use the same UpgradeAway-style pattern as BPRUE Main.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    rendered: list[tuple[str, str]] = []
    for technician_sid, technician_upgrades in sorted(assignments.items()):
        list_sid = f"BPRUE_Armor_{technician_sid}_UpgradeList"
        rendered.append((technician_sid, list_sid))
        unique = {upgrade.sid: upgrade for upgrade in technician_upgrades}
        lines.append(f"{list_sid} : struct.begin")
        for upgrade in sorted(unique.values(), key=lambda u: (u.armor_sid, u.tier_index)):
            lines += [
                f"   {upgrade.sid} : struct.begin",
                f"      UpgradePrototypeSID = {upgrade.sid}",
                "      Enabled = true",
                "   struct.end",
            ]
        lines += ["struct.end", ""]

    for technician_sid, list_sid in rendered:
        lines += [
            f"{technician_sid} : struct.begin {{bpatch}}",
            f"   Upgrades : struct.begin {{bpatch;refkey={list_sid}}}",
            "   struct.end",
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    upgrades = build_upgrades()
    for path in (ARMOR_PATCH_PATH, UPGRADE_OUTPUT_PATH, EFFECT_OUTPUT_PATH, NPC_OUTPUT_PATH):
        path.parent.mkdir(parents=True, exist_ok=True)

    upgrade_text = render_upgrade_fragment(upgrades)
    armor_patch_text = render_armor_patch(upgrades)
    effect_text = render_effects(load_config())
    npc_text = render_npc_patch(upgrades)

    UPGRADE_OUTPUT_PATH.write_text(upgrade_text, encoding="utf-8")
    ARMOR_PATCH_PATH.write_text(armor_patch_text, encoding="utf-8")
    EFFECT_OUTPUT_PATH.write_text(effect_text, encoding="utf-8")
    NPC_OUTPUT_PATH.write_text(npc_text, encoding="utf-8")

    # Guard the module boundary: this generator must never write into Main/GameLite.
    for path in (ARMOR_PATCH_PATH, UPGRADE_OUTPUT_PATH, EFFECT_OUTPUT_PATH, NPC_OUTPUT_PATH):
        if ARMOR_ROOT not in path.parents:
            raise ValueError(f"Armor generator attempted to write outside Armor/: {path}")

    print(f"Generated {len(upgrades)} armor signature upgrade instances")
    print(f"Armor module root: {ARMOR_ROOT}")
    print(f"Generated {UPGRADE_OUTPUT_PATH}")
    print(f"Generated {ARMOR_PATCH_PATH}")
    print(f"Generated {EFFECT_OUTPUT_PATH}")
    print(f"Generated {NPC_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
