import logging
import os

db_logger = logging.getLogger("dblogger")
db_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(os.path.join("aimods_bot", "misc", "logs", "database.log"))
file_handler.setFormatter(formatter)
db_logger.addHandler(file_handler)