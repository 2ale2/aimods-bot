import logging

# logger del database
db_logger = logging.getLogger("dblogger")
db_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler("../misc/logs/database.log")
file_handler.setFormatter(formatter)
db_logger.addHandler(file_handler)

# logger dei comandi
command_logger = logging.getLogger("commandlogger")
command_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("../misc/logs/commands.log")
file_handler.setFormatter(formatter)
command_logger.addHandler(file_handler)

# logger della queue
job_queue_logger = logging.getLogger("jobqueuelogger")
job_queue_logger.setLevel(logging.WARNING)
file_handler = logging.FileHandler("../misc/logs/jobqueue.log")
file_handler.setFormatter(formatter)
job_queue_logger.addHandler(file_handler)
