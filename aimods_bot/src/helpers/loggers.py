import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "bot.log")

# Logger principale
logger = logging.getLogger("bot")
logger.setLevel(logging.INFO)

# Rotating file handler
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=2_000_000, backupCount=3)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    "%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(file_formatter)
logger.addHandler(console_handler)

# Silenzia il root logger se non serve
# logging.getLogger().setLevel(logging.WARNING)
