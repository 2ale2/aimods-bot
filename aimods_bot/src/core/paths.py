from pathlib import Path

# core/ → src/ → aimods_bot/
PACKAGE_ROOT = Path(__file__).resolve().parents[2]

MISC_DIR = PACKAGE_ROOT / "misc"
MINIAPP_STATIC_DIR = MISC_DIR / "miniapp_static"
