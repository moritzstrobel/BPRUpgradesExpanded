from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON_ROOT = SCRIPT_DIR.parents[1]
CONTENT_ROOT = PYTHON_ROOT.parent
CONFIG_PATH = SCRIPT_DIR / "armor_signatures.json"
CLASSIFICATION_PATH = PYTHON_ROOT / "AnalysisArmor" / "Reports" / "armor_classification.json"
UPGRADE_MAPPING_PATH = PYTHON_ROOT / "AnalysisArmor" / "Reports" / "armor_upgrade_mapping.json"
UPGRADE_DETAILS_PATH = PYTHON_ROOT / "AnalysisArmor" / "Reports" / "armor_upgrade_details.json"
MAX_VISIBLE_HORIZONTAL_POSITION = 2
VERTICALS = ("Top", "Down", None)
ARMOR_TARGET_ORDER = ("Body", "Barrel", "Handguard", "PistolGrip", "Stock")

ARMOR_PATCH_PATH = CONTENT_ROOT / "GameLite/GameData/ItemPrototypes/ArmorPrototypes/ArmorPrototypes_patch_BPRUE.cfg"
EFFECT_OUTPUT_PATH = CONTENT_ROOT / "GameLite/ModGameData/BPRUpgradesExpanded/EffectPrototypes/BPRUE_ArmorEffectPrototypes.cfg"

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


DEFAULT_ICON = "Texture2D'/Game/GameLite/FPS_Game/UIRemaster/UITextures/PDA/Upgrades/Icons/Armor/T_PDA_Upgrades_Icon_AttachmentSystem.T_PDA_Upgrades_Icon_AttachmentSystem'"


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
    horizontal_position: int | None = None
    vertical_position: str | None = None


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_classification() -> dict:
    if not CLASSIFICATION_PATH.exists():
        raise FileNotFoundError(
            f"{CLASSIFICATION_PATH} missing; run Python/AnalysisArmor/classify_armor.py first"
        )
    return json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))


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
            result.append(ArmorUpgradeDefinition(
                sid=f"{armor_sid}_Upgrade_BPRUE_{faction}_Signature",
                armor_sid=armor_sid,
                faction=faction,
                category=category,
                signature=faction_cfg["signature"],
                target_part=category_cfg["target_part"],
                text_sid=category_cfg["text_sid"],
                hint_sid=category_cfg["hint_sid"],
                cost=int(category_cfg["cost"]),
                effects=tuple(category_cfg["effects"]),
            ))

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

    vanilla_by_armor = _vanilla_upgrade_sids_by_armor()
    details = _upgrade_details()
    resolved: list[ArmorUpgradeDefinition] = []
    for upgrade in upgrades:
        vanilla_sids = vanilla_by_armor.get(upgrade.armor_sid)
        if vanilla_sids is None:
            raise ValueError(f"{upgrade.armor_sid}: missing Vanilla UpgradePrototypeSIDs mapping")
        occupied = _vanilla_module_columns(upgrade.armor_sid, vanilla_sids, details)
        target, horizontal = _first_free_armor_column(upgrade.target_part, occupied)
        resolved.append(replace(
            upgrade,
            target_part=target,
            horizontal_position=None if horizontal == 0 else horizontal,
            vertical_position=VERTICALS[0],
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
    if errors:
        raise ValueError("Invalid BPRUE armor signature model:\n  - " + "\n  - ".join(errors))


def render_upgrade_fragment(upgrades: list[ArmorUpgradeDefinition]) -> str:
    lines = [
        "// -----------------------------------------------------------------------------",
        "// BPRUE ARMOR SIGNATURE UPGRADES",
        "// Generated by CFGGenerators/Armor/generate_armor_signatures.py",
        "// This is a fragment appended to the consolidated BPRUE UpgradePrototypes file.",
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
            f"   Image = {faction_module_image(upgrade.faction)}",
            f"   Icon = {DEFAULT_ICON}",
            f"   BaseCost = {upgrade.cost}",
            *([f"   HorizontalPosition = {upgrade.horizontal_position}"] if upgrade.horizontal_position is not None else []),
            *([f"   VerticalPosition = EUpgradeVerticalPosition::{upgrade.vertical_position}"] if upgrade.vertical_position is not None else []),
            f"   UpgradeTargetPart = EUpgradeTargetPartType::{upgrade.target_part}",
            "   EffectPrototypeSIDs : struct.begin",
            *(f"      [{i}] = {effect}" for i, effect in enumerate(upgrade.effects)),
            "   struct.end",
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
    by_armor = {upgrade.armor_sid: upgrade for upgrade in upgrades}
    vanilla_by_armor = _vanilla_upgrade_sids_by_armor()
    lines = [
        "// -----------------------------------------------------------------------------",
        "// AUTO-GENERATED FILE - DO NOT EDIT BY HAND",
        "// Adds BPRUE faction signature modules to player armor without replacing",
        "// the armor's existing Vanilla UpgradePrototypeSIDs array.",
        "// -----------------------------------------------------------------------------",
        "",
    ]
    for armor_sid, upgrade in sorted(by_armor.items()):
        vanilla = vanilla_by_armor.get(armor_sid)
        if vanilla is None:
            raise ValueError(f"{armor_sid}: missing Vanilla UpgradePrototypeSIDs mapping")
        combined = list(dict.fromkeys([*vanilla, upgrade.sid]))
        lines += [
            f"{armor_sid} : struct.begin {{bpatch}}",
            "   UpgradePrototypeSIDs : struct.begin",
            *(f"      [{i}] = {sid}" for i, sid in enumerate(combined)),
            "   struct.end",
            "struct.end",
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def render_effects() -> str:
    return r"""// AUTO-GENERATED - BPRUE armor faction signature effects
// Prototype faction: FREEDOM / Mobility.
// Values are intentionally isolated here so signature balancing does not touch weapon effects.

BPRUE_Armor_Freedom_Helmet_Weight : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Armor_Freedom_Helmet_Weight
   LocalizationSID = armor_reductionWeight
   Text = Item Weight
   Type = EEffectType::ArmorItemWeight
   ValueMin = -0.5
   ValueMax = -0.5
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end

BPRUE_Armor_Freedom_Suit_Weight : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Armor_Freedom_Suit_Weight
   LocalizationSID = armor_reductionWeight
   Text = Item Weight
   Type = EEffectType::ArmorItemWeight
   ValueMin = -1
   ValueMax = -1
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end

BPRUE_Armor_Freedom_Suit_Stamina : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Armor_Freedom_Suit_Stamina
   LocalizationSID = Armor_regenerationStamina
   Text = Regen Stamina
   Type = EEffectType::RegenStamina
   ValueMin = 5.0%
   ValueMax = 5.0%
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end

BPRUE_Armor_Freedom_FullBody_Weight : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Armor_Freedom_FullBody_Weight
   LocalizationSID = armor_reductionWeight
   Text = Item Weight
   Type = EEffectType::ArmorItemWeight
   ValueMin = -1
   ValueMax = -1
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end

BPRUE_Armor_Freedom_FullBody_Stamina : struct.begin {refurl=@BaseGame/EffectPrototypes.cfg;refkey=[0]}
   SID = BPRUE_Armor_Freedom_FullBody_Stamina
   LocalizationSID = Armor_regenerationStamina
   Text = Regen Stamina
   Type = EEffectType::RegenStamina
   ValueMin = 5.0%
   ValueMax = 5.0%
   bIsPermanent = true
   Positive = EBeneficial::Positive
struct.end
"""


def main() -> None:
    upgrades = build_upgrades()
    ARMOR_PATCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    EFFECT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARMOR_PATCH_PATH.write_text(render_armor_patch(upgrades), encoding="utf-8")
    EFFECT_OUTPUT_PATH.write_text(render_effects(), encoding="utf-8")
    print(f"Generated {len(upgrades)} armor signature upgrade instances")
    print(f"Generated {ARMOR_PATCH_PATH}")
    print(f"Generated {EFFECT_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
