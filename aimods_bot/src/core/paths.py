from pathlib import Path

# constants/ → helpers/ → src/ → aimods_bot/
PACKAGE_ROOT = Path(__file__).resolve().parents[3]

MISC_DIR = PACKAGE_ROOT / "misc"
MINIAPP_STATIC_DIR = MISC_DIR / "miniapp_static"
