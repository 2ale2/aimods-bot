import logging
import os.path

# logger del database
db_logger = logging.getLogger("dblogger")
db_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(os.path.join("aimods_bot", "misc", "logs", "database.log"))
file_handler.setFormatter(formatter)
db_logger.addHandler(file_handler)

# logger dei comandi
bot_logger = logging.getLogger("botlogger")
bot_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(os.path.join("aimods_bot", "misc", "logs", "bot.log"))
file_handler.setFormatter(formatter)
bot_logger.addHandler(file_handler)

# logger della queue
job_queue_logger = logging.getLogger("jobqueuelogger")
job_queue_logger.setLevel(logging.WARNING)
file_handler = logging.FileHandler(os.path.join("aimods_bot", "misc", "logs", "jobqueue.log"))
file_handler.setFormatter(formatter)
job_queue_logger.addHandler(file_handler)
