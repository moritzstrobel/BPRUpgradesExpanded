from pathlib import Path

ANALYSIS_DIR = Path(__file__).resolve().parent
REPORTS_DIR = ANALYSIS_DIR / "Reports"

VANILLA_UPGRADE_MAP = REPORTS_DIR / "vanilla_upgrade_map.json"
BPRUE_UPGRADE_MAP = REPORTS_DIR / "bprue_upgrade_map.json"
UPGRADE_MAP_COMPARISON = REPORTS_DIR / "upgrade_map_comparison.json"
UPGRADE_LAYOUT_ANALYSIS = REPORTS_DIR / "upgrade_layout_analysis.json"
WEAPON_UPGRADE_SECTIONS = REPORTS_DIR / "weapon_upgrade_sections.json"
WEAPON_COVERAGE = REPORTS_DIR / "weapon_coverage.json"
TECHNICIAN_UPGRADE_MAP = REPORTS_DIR / "technician_upgrade_map.json"


def ensure_reports_dir() -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return REPORTS_DIR
